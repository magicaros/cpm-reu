#!/usr/bin/env python3
"""
reuimg.py - read the REUDISK B: file system out of a VICE REU image
(x64sc -reuimage FILE -reuimagerw saves the 512 KB REU contents on exit).

Drive B: geometry (src/reudrv.z80): 128 records/track, 2 KB blocks,
DSM=255, DRM=127, AL0=$C0, OFF=0, EXM=1.  REU byte address = record * 128.

Usage:
    reuimg.py reu.img ls
    reuimg.py reu.img get NAME.EXT [hostfile]
    reuimg.py reu.img verify DISK.d64     compare every B: file with A: copy
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cpmd64  # noqa: E402

BLS, DRM, REC = 2048, 127, 128


def files(img):
    res = {}
    for i in range(DRM + 1):
        e = img[i * 32:(i + 1) * 32]
        if e[0] > 15:
            continue
        name = cpmd64.CpmDisk.name_of(e)
        res.setdefault(name, []).append(e)
    return res


def get(img, name):
    ents = sorted(files(img)[name], key=lambda e: e[12] + 32 * e[14])
    out = bytearray()
    for e in ents:
        # EXM=1: one directory entry = 2 logical extents, 8 x 16-bit... no:
        # DSM<256 -> 16 one-byte block pointers per entry (16 x 2 KB = 32 KB)
        data = bytearray()
        for b in e[16:32]:
            if b:
                data += img[b * BLS:(b + 1) * BLS]
        recs = (e[12] & 1) * 128 + e[15]      # records in this entry
        out += data[:recs * REC]
    return bytes(out)


def main(argv):
    if len(argv) < 3:
        raise SystemExit(__doc__)
    img = open(argv[1], 'rb').read()
    cmd = argv[2]
    if cmd == 'ls':
        for n, ents in sorted(files(img).items()):
            print('%-12s %6d bytes' % (n, len(get(img, n))))
    elif cmd == 'get':
        open(argv[4] if len(argv) > 4 else argv[3].lower(), 'wb').write(get(img, argv[3]))
    elif cmd == 'verify':
        disk = cpmd64.CpmDisk(argv[3])
        bad = 0
        for n in sorted(files(img)):
            src = n if n != 'PIP2.COM' else 'PIP.COM'
            try:
                ref = disk.get(src)
            except SystemExit:
                print('%-12s (not on A:, skipped)' % n)
                continue
            got = get(img, n)
            ok = got == ref
            bad += not ok
            print('%-12s %6d bytes  %s' % (n, len(got), 'OK' if ok else 'MISMATCH'))
        raise SystemExit(1 if bad else 0)
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main(sys.argv)
