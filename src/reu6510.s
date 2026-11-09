; =============================================================================
;  reu6510.s  -  6510 side of the C64 CP/M 2.2 REU RAM-disk (drive B:)
; =============================================================================
;
;  Assembler : ca65 (cc65 suite)          ld65 config: src/reu6510.cfg
;  Load addr : 6510 $0980  (= Z80 $F980 because Z80 addr = 6510 addr - $1000)
;
;  UNIVERSAL PLACEMENT (44K, 48K, AND SOFT80 COMPATIBLE)
;  -----------------------------------------------------
;  Page $0900-$09FF (Z80 $F900-$F9FF) is the BIOS65 communication page:
;      $0900-$0907  Command/data/sector/track/drive/key/indirect vector
;      $0908-$09FE  Completely unused by BIOS65, CP/M 44K/48K, and SOFT80.COM
;      $09FF        Printer status byte
;  Placing the 16-byte parameter block at $0980-$098F and the 6510 REU DMA
;  trampoline at $0990-$09BF avoids touching $C000-$CFFF (which holds the
;  48K BDOS/BIOS on 48K CP/M disks) and avoids $0400-$05FF / $D000-$FFFF
;  (which are used by SOFT80.COM).
;
;  HOW THE 6510 GETS HERE
;  ----------------------
;  The Commodore CP/M cartridge alternates the two CPUs through IO1 ($DE00):
;
;    6510 BIOS65 main loop (resident at 6510 $0A00, unchanged by us):
;
;        $0A00  LDA #$00
;        $0A02  STA $DE00      ; hand the bus to the Z80, 6510 freezes HERE
;        $0A05  NOP            ; <- resumes here when the Z80 writes 1 to $CE00
;        $0A06  JSR $0A0C      ; dispatch on command byte at $0900
;        $0A09  JMP $0A00      ; ...and give the bus back to the Z80
;
;    The dispatcher at $0A0C jumps through a table at $0A28; command 9 is the
;    "user" command:   $0A3C  JMP ($0906)
; =============================================================================

        .setcpu "6502"

; --- Commodore 1700/1750/1764 REU registers (IO2) ----------------------------
REU_STATUS  = $DF00     ; R : b7 IRQ, b6 end-of-block, b5 verify err, b4 256K chips
REU_CMD     = $DF01     ; W : b7 execute, b5 autoload, b4 1=no $FF00 trigger,
                        ;     b1-0: 00 C64->REU (stash) 01 REU->C64 (fetch)
REU_C64LO   = $DF02     ; C64 base address
REU_C64HI   = $DF03
REU_REULO   = $DF04     ; REU base address (bits 0-15)
REU_REUHI   = $DF05
REU_BANK    = $DF06     ; REU bank (bits 16-23, 0-7 for a 512 KB 1750)
REU_LENLO   = $DF07     ; transfer length ($0000 = 64 KB)
REU_LENHI   = $DF08
REU_IMASK   = $DF09     ; interrupt mask
REU_ACR     = $DF0A     ; address control: b7 fix C64 addr, b6 fix REU addr

        .segment "CODE"

; =============================================================================
;  Shared parameter block - 6510 $0980..$098F  /  Z80 $F980..$F98F
;  Bytes +1..+10 are laid out exactly like REU registers $DF01..$DF0A so the
;  copy loop below is a straight indexed move.  Filled by the Z80 driver.
; =============================================================================
PB:
PB_MAGIC:   .byte $65           ; +0  marker (lets the installer sanity-check)
PB_CMD:     .byte $00           ; +1  -> $DF01 ($90 = stash, $91 = fetch)
PB_C64:     .word $0000         ; +2  -> $DF02/03  6510 address (Z80 DMA+$1000)
PB_REU:     .word $0000         ; +4  -> $DF04/05  REU address
PB_BANK:    .byte $00           ; +6  -> $DF06     REU bank
PB_LEN:     .word $0080         ; +7  -> $DF07/08  length (128 = one CP/M record)
PB_IMASK:   .byte $00           ; +9  -> $DF09     no REU interrupts
PB_ACR:     .byte $00           ; +10 -> $DF0A     0 = both addresses increment
PB_STATUS:  .byte $00           ; +11 <- $DF00 after the transfer
            .res  4, $00        ; +12..+15 reserved

; =============================================================================
;  ENTRY - 6510 $0990.  Reached by JSR $0A0C -> JMP ($0A3A) -> JMP ($0906).
;  In : parameter block above.     Out: PB_STATUS = REU status register.
;  Preserves the caller's interrupt flag and 6510 $01 memory banking.
; =============================================================================
ENTRY:
        php                     ; remember the I flag BIOS65 runs with
        sei                     ; block IRQs during REU register setup & DMA
        cld

        lda     $01             ; save 6510 processor port
        pha
        lda     #$35            ; bank out BASIC ($A000-$BFFF) and KERNAL
        sta     $01             ; ($E000-$FFFF) -> ALL RAM visible to REU DMA
                                ; except I/O ($D000-$DFFF -> REU at $DF00)!

        ldx     #9              ; copy PB+2..PB+10 -> $DF02..$DF0A (X = 9..1)
@copy:  lda     PB_CMD,x
        sta     REU_CMD,x
        dex
        bne     @copy

        lda     REU_STATUS      ; reading $DF00 clears stale EOB/IRQ bits

        lda     PB_CMD          ; bit7=execute, bit4=start now (no $FF00 wait)
        sta     REU_CMD         ; the REU asserts DMA and freezes the 6510
                                ; until all bytes are moved (1 byte/cycle)

        lda     REU_STATUS      ; b6 = end of block -> Z80 checks it
        sta     PB_STATUS       ; (read also acknowledges the status)

        pla                     ; restore 6510 processor port ($01 = $36)
        sta     $01
        plp                     ; restore the caller's interrupt state
        rts                     ; back to BIOS65 -> LDA #0 / STA $DE00 -> Z80
ENTRY_END:

        .assert ENTRY = PB + 16, error, "ENTRY must sit at $0920"
        .assert ENTRY_END <= $0950, lderror, "6510 module must fit in 64 bytes"
