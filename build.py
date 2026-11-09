#!/usr/bin/env python3
"""
build.py - build REUDISK.COM and a bootable test disk for VICE.

Requirements:  cc65 (ca65 + ld65), pasmo, python3, and your own copy of the
Commodore 64 CP/M 2.2 system disk (.d64) - it is not redistributable.

    python3 build.py --cpm-disk /path/to/c64-cpm.d64 [--test]

Outputs (in build/):
    reu6510.bin   6510 trampoline (one page, loads at 6510 $C000)
    reudrv.bin    resident block (Z80 $B000-...), reudrv.sym its public labels
    REUDISK.COM   CP/M installer
    cpm-reu.d64   copy of the CP/M disk with REUDISK.COM added
                  (--test also adds a $$$.SUB that installs B: and copies
                   all of A: to B: automatically at boot)
"""
import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
BUILD = os.path.join(ROOT, 'build')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import cpmd64  # noqa: E402


def run(*cmd, cwd=BUILD):
    print('  $', ' '.join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def tool(name):
    path = os.environ.get(name.upper()) or shutil.which(name)
    if not path:
        sys.exit('error: %s not found (install it or set $%s)' % (name, name.upper()))
    return path


def make_submit(commands):
    """CP/M $$$.SUB: one 128-byte record per command, LAST command first."""
    out = bytearray()
    for c in reversed(commands):
        c = c.upper().encode()
        out += bytes([len(c)]) + c + b'\x00' + b'\x1a' * (126 - len(c))
    return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cpm-disk', default=os.path.join(ROOT, 'cpm80.d64'),
                    help='original Commodore 64 CP/M 2.2 boot disk (.d64)')
    ap.add_argument('--test', action='store_true',
                    help='add an auto-running $$$.SUB test script to the disk')
    args = ap.parse_args()

    os.makedirs(BUILD, exist_ok=True)
    ca65, ld65, pasmo = tool('ca65'), tool('ld65'), tool('pasmo')

    print('[1/4] 6510 trampoline')
    run(ca65, '-o', 'reu6510.o', '-l', 'reu6510.lst', os.path.join(SRC, 'reu6510.s'))
    run(ld65, '-C', os.path.join(SRC, 'reu6510.cfg'), '-o', 'reu6510.bin', 'reu6510.o')
    assert os.path.getsize(os.path.join(BUILD, 'reu6510.bin')) == 64

    print('[2/4] Z80 resident driver')
    run(pasmo, '--public', '-I', SRC, '-I', BUILD,
        os.path.join(SRC, 'reudrv.z80'), 'reudrv.bin', 'reudrv.sym')

    print('[3/4] Z80 installer')
    run(pasmo, '-I', SRC, '-I', BUILD,
        os.path.join(SRC, 'install.z80'), 'REUDISK.COM')

    print('[4/4] disk image')
    disk = os.path.join(BUILD, 'cpm-reu.d64')
    shutil.copyfile(args.cpm_disk, disk)
    d = cpmd64.CpmDisk(disk)
    with open(os.path.join(BUILD, 'REUDISK.COM'), 'rb') as f:
        d.put('REUDISK.COM', f.read())
    if args.test:
        # On cpm80.d64, BIOS MSGPTR at $BA66 (T2 S11 +0x66) is pre-loaded with
        # $FC82 ("SOFT80\r") so CONST returns 0FFh at boot, which would cause
        # the CCP to abort $$$.SUB. Zeroing MSGPTR lets $$$.SUB run SOFT80 +
        # REUDISK + PIP unattended.
        t2s11 = cpmd64.d64_offset(2, 11)
        if d.img[t2s11 + 0x66:t2s11 + 0x68] == b'\x82\xfc':
            d.img[t2s11 + 0x66:t2s11 + 0x68] = b'\x00\x00'
        d.put('$$$.SUB', make_submit([
            'SOFT80',
            'REUDISK',
            'STAT B:DSK:',
            'PIP B:=A:*.COM[V]',
            'B:',
            'PIP B:PIP2.COM=B:PIP.COM[V]',
            'DIR',
            'STAT',
        ]))
    d.save()
    d.ls()
    print('\nbuilt', os.path.relpath(disk, ROOT))


if __name__ == '__main__':
    main()
