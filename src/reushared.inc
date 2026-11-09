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

; --- 6510 trampoline (src/reu6510.s), assembled for 6510 $C000 ----------------
RES_BASE    EQU 0B000h  ; Z80 address of the resident block (6510 $C000)
ENTRY65     EQU 0C010h  ; 6510 address of ENTRY (stored into $0906)
PB          EQU 0B000h  ; parameter block, Z80 view of 6510 $C000
PB_MAGIC    EQU PB+0    ; $65 when the 6510 module is present
PB_CMD      EQU PB+1    ; -> $DF01
PB_C64      EQU PB+2    ; -> $DF02/03 (6510 address = Z80 address + $1000)
PB_REU      EQU PB+4    ; -> $DF04/05
PB_BANK     EQU PB+6    ; -> $DF06
PB_LEN      EQU PB+7    ; -> $DF07/08
PB_IMASK    EQU PB+9    ; -> $DF09
PB_ACR      EQU PB+10   ; -> $DF0A
PB_STATUS   EQU PB+11   ; <- $DF00

; --- REU commands / flags -----------------------------------------------------
REU_STASH   EQU 090h    ; execute, immediate (no $FF00 trigger), C64 -> REU
REU_FETCH   EQU 091h    ; execute, immediate, REU -> C64
REU_EOB     EQU 040h    ; status bit 6: end of block (transfer completed)
ACR_FIXC64  EQU 080h    ; address control: C64 address does not increment

; --- Z80 -> 6510 address translation ------------------------------------------
Z2C         EQU 1000h   ; add to a Z80 address to get the 6510/REU-DMA address

; --- Stock C64 CP/M 2.2 (44K) layout ------------------------------------------
BIOS_BASE   EQU 0AA00h  ; BIOS jump table (WBOOT vector at 0001 = $AA03)

; --- RAM-disk geometry (drive B:) ---------------------------------------------
B_SPT       EQU 128     ; 128-byte records per track (16 KB tracks)
B_TRACKS    EQU 32      ; 32 tracks * 16 KB = 512 KB = REU banks 0..7
