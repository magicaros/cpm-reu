; =============================================================================
;  reushared.inc - constants shared by the resident driver and the installer
; =============================================================================

; --- Commodore CP/M cartridge: CPU switch and BIOS65 mailbox -----------------
; Z80 address = 6510 address - $1000 (mod 64K)
CPUSWITCH   EQU 0CE00h  ; Z80 $CE00 = 6510 $DE00 (IO1). Write 1: Z80 off, 6510 on
B65CMD      EQU 0F900h  ; 6510 $0900: BIOS65 command byte
B65VEC      EQU 0F906h  ; 6510 $0906: BIOS65 command-9 "user" vector (JMP ($0906))
B65USER     EQU 9       ; BIOS65 command number for "JMP ($0906)"
B65CHK      EQU 0FA3Ch  ; 6510 $0A3C: should hold 6C 06 09 = JMP ($0906)

; --- Universal Low-RAM Layout (works on 20K..48K TPA AND with SOFT80.COM) -----
; 6510 $0880..$08FF (Z80 $F880..$F8FF):
;   $0800..$087F  256-byte disk sector buffer ($0800-$08FF) -> wait: $0800-$08FF
;                 is HSTBUF ($F800-$F8FF)!
; Where did $F910-$F9EF collide with SOFT80?
; Let's check SOFT80_6510.ASM and BIOS65 ($0A00-$0DFF)!
TRAMP_Z80   EQU 0F910h  ; Z80 view of 6510 $0910
ENTRY65     EQU 00920h  ; 6510 address of ENTRY (stored into $0906)
PB          EQU 0F910h  ; parameter block, Z80 view of 6510 $0910
PB_MAGIC    EQU PB+0    ; $65 when the 6510 module is present
PB_CMD      EQU PB+1    ; -> $DF01
PB_C64      EQU PB+2    ; -> $DF02/03 (6510 address = Z80 address + $1000)
PB_REU      EQU PB+4    ; -> $DF04/05
PB_BANK     EQU PB+6    ; -> $DF06
PB_LEN      EQU PB+7    ; -> $DF07/08
PB_IMASK    EQU PB+9    ; -> $DF09
PB_ACR      EQU PB+10   ; -> $DF0A
PB_STATUS   EQU PB+11   ; <- $DF00
ALV_B_Z80   EQU 0F950h  ; 32-byte ALV_B in unused $0950-$096F (Z80 $F950-$F96F)
DIRBF_B_Z80 EQU 0F970h  ; 128-byte DIRBUF_B in unused $0970-$09EF (Z80 $F970-$F9EF)

RES_BASE    EQU 0FE00h  ; Z80 address of the resident Z80 driver (6510 $0E00)

; --- REU commands / flags -----------------------------------------------------
REU_STASH   EQU 090h    ; execute, immediate (no $FF00 trigger), C64 -> REU
REU_FETCH   EQU 091h    ; execute, immediate, REU -> C64
REU_EOB     EQU 040h    ; status bit 6: end of block (transfer completed)
ACR_FIXC64  EQU 080h    ; address control: C64 address does not increment

; --- Z80 -> 6510 address translation ------------------------------------------
Z2C         EQU 1000h   ; add to a Z80 address to get the 6510/REU-DMA address

; --- RAM-disk geometry (drive B:) & Instant Warm-Boot Cache -------------------
; Track 0 (REU bank 0, $0000-$3FFF) is reserved (OFF = 1) and stores the 5.5 KB
; CCP+BDOS snapshot ($1600 bytes at REU bank 0, $0000-$15FF) so every WBOOT
; reloads CCP+BDOS from REU DMA in ~5.6 ms instead of 15 seconds from floppy!
B_SPT       EQU 128     ; 128-byte records per track (16 KB tracks)
B_TRACKS    EQU 32      ; 32 tracks * 16 KB = 512 KB = REU banks 0..7
B_OFF       EQU 1       ; 1 reserved system track (Track 0 = CCP+BDOS REU cache)
B_DSM       EQU 247     ; 248 data blocks * 2 KB = 496 KB (Tracks 1..31)
WB_LEN      EQU 1600h   ; 22 pages (5632 bytes) = CCP ($800) + BDOS ($E00)
