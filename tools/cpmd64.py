#!/usr/bin/env python3
"""
cpmd64.py - minimal file manager for the Commodore 64 CP/M 2.2 disk format
inside a .D64 image (the format written by the Commodore Z80 cartridge BIOS).

Disk geometry (taken from the live BIOS / DPB found at Z80 $AA54):
    SPT = 34 (128-byte records = 17 CBM 256-byte sectors per track)
    BSH = 3, BLM = 7  -> 1 KB allocation blocks
    EXM = 0, DSM = 135 (136 blocks), DRM = 63 (64 directory entries)
    AL0 = $C0         -> blocks 0 and 1 hold the directory
    OFF = 2           -> two reserved system tracks

Logical -> physical mapping (from the BIOS write path at $AE4C):
    CBM track  = CP/M track + 1, plus 1 more if the result is >= 18
                 (CBM directory track 18 is skipped)
    CBM sector = CP/M sector >> 1   (only sectors 0..16 of every track are used)
    half       = CP/M sector & 1    (two 128-byte records per 256-byte sector)

Usage:
    cpmd64.py IMAGE.d64 ls
    cpmd64.py IMAGE.d64 get CPMNAME.EXT [hostfile]
    cpmd64.py IMAGE.d64 put hostfile [CPMNAME.EXT]
    cpmd64.py IMAGE.d64 rm CPMNAME.EXT
"""
import os
import sys

SPT = 34
BLS = 1024
DSM = 135
DRM = 63
OFF = 2
REC = 128
RECS_PER_BLOCK = BLS // REC
DIR_BLOCKS = 2


def d64_offset(track, sector):
    """Byte offset of CBM (track, sector) in a 35-track D64."""
    off = 0
    for t in range(1, track):
        off += 21 if t <= 17 else 19 if t <= 24 else 18 if t <= 30 else 17
    return (off + sector) * 256


class CpmDisk:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            self.img = bytearray(f.read())

    def save(self):
        with open(self.path, 'wb') as f:
            f.write(self.img)

    # --- record level ------------------------------------------------------
    def _rec_offset(self, track, sector):
        ct = track + 1
        if ct >= 18:
            ct += 1
        return d64_offset(ct, sector >> 1) + (sector & 1) * REC

    def _data_rec_offset(self, r):
        """Offset of record r counted from the start of the data area (OFF)."""
        return self._rec_offset(OFF + r // SPT, r % SPT)

    def read_block(self, b):
        out = bytearray()
        for k in range(RECS_PER_BLOCK):
            o = self._data_rec_offset(b * RECS_PER_BLOCK + k)
            out += self.img[o:o + REC]
        return out

    def write_block(self, b, data):
        data = bytes(data).ljust(BLS, b'\x1a')
        for k in range(RECS_PER_BLOCK):
            o = self._data_rec_offset(b * RECS_PER_BLOCK + k)
            self.img[o:o + REC] = data[k * REC:(k + 1) * REC]

    # --- directory ---------------------------------------------------------
    def dir_entries(self):
        raw = self.read_block(0) + self.read_block(1)
        return [bytearray(raw[i * 32:(i + 1) * 32]) for i in range(DRM + 1)]

    def write_dir(self, ents):
        raw = b''.join(bytes(e) for e in ents)
        self.write_block(0, raw[:BLS])
        self.write_block(1, raw[BLS:])

    @staticmethod
    def name_of(e):
        n = bytes(c & 0x7f for c in e[1:9]).decode('ascii').rstrip()
        x = bytes(c & 0x7f for c in e[9:12]).decode('ascii').rstrip()
        return n + ('.' + x if x else '')

    @staticmethod
    def make_name(name):
        name = name.upper()
        base, _, ext = name.partition('.')
        return base[:8].ljust(8).encode() + ext[:3].ljust(3).encode()

    def files(self):
        res = {}
        for e in self.dir_entries():
            if e[0] == 0xE5 or e[0] > 15:
                continue
            res.setdefault((e[0], self.name_of(e)), []).append(e)
        return res

    def used_blocks(self):
        used = set(range(DIR_BLOCKS))
        for e in self.dir_entries():
            if e[0] == 0xE5 or e[0] > 15:
                continue
            used.update(b for b in e[16:32] if b)
        return used

    # --- commands ----------------------------------------------------------
    def ls(self):
        for (user, name), ents in sorted(self.files().items()):
            recs = sum(e[15] for e in ents)
            print('%2d: %-12s %4d records (%d bytes)' % (user, name, recs, recs * REC))
        free = (DSM + 1 - len(self.used_blocks())) * BLS // 1024
        print('free: %d KB' % free)

    def get(self, name):
        ents = self.files().get((0, name.upper()))
        if not ents:
            raise SystemExit('not found: ' + name)
        ents.sort(key=lambda e: e[12] + 32 * e[14])
        out = bytearray()
        for e in ents:
            data = bytearray()
            for b in e[16:32]:
                if b:
                    data += self.read_block(b)
            out += data[:e[15] * REC]
        return bytes(out)

    def rm(self, name):
        key = self.make_name(name)
        ents = self.dir_entries()
        hit = False
        for e in ents:
            if e[0] == 0 and bytes(c & 0x7f for c in e[1:12]) == key:
                e[0] = 0xE5
                hit = True
        self.write_dir(ents)
        return hit

    def put(self, name, data):
        self.rm(name)
        ents = self.dir_entries()
        used = self.used_blocks()
        free = [b for b in range(DIR_BLOCKS, DSM + 1) if b not in used]
        nrec = (len(data) + REC - 1) // REC
        data = data.ljust(nrec * REC, b'\x1a')
        nblk = (nrec + RECS_PER_BLOCK - 1) // RECS_PER_BLOCK
        if nblk > len(free):
            raise SystemExit('disk full')
        blocks = free[:nblk]
        for i, b in enumerate(blocks):
            self.write_block(b, data[i * BLS:(i + 1) * BLS])
        # one extent = 16 blocks (EXM=0, 8-bit block numbers) = 128 records
        ext = 0
        while True:
            chunk = blocks[ext * 16:(ext + 1) * 16]
            recs = min(128, nrec - ext * 128)
            slot = next((i for i, e in enumerate(ents) if e[0] == 0xE5), None)
            if slot is None:
                raise SystemExit('directory full')
            e = bytearray(32)
            e[0] = 0
            e[1:12] = self.make_name(name)
            e[12] = ext & 0x1f
            e[14] = ext >> 5
            e[15] = recs
            for i, b in enumerate(chunk):
                e[16 + i] = b
            ents[slot] = e
            ext += 1
            if ext * 128 >= nrec:
                break
        self.write_dir(ents)


def main(argv):
    if len(argv) < 3:
        raise SystemExit(__doc__)
    disk = CpmDisk(argv[1])
    cmd = argv[2]
    if cmd == 'ls':
        disk.ls()
    elif cmd == 'get':
        data = disk.get(argv[3])
        with open(argv[4] if len(argv) > 4 else argv[3].lower(), 'wb') as f:
            f.write(data)
    elif cmd == 'put':
        host = argv[3]
        name = argv[4] if len(argv) > 4 else os.path.basename(host)
        with open(host, 'rb') as f:
            disk.put(name, f.read())
        disk.save()
    elif cmd == 'rm':
        if not disk.rm(argv[3]):
            raise SystemExit('not found: ' + argv[3])
        disk.save()
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main(sys.argv)
