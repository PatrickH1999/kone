KONESTD___start:
    JMP main            // Line 0,1

KONESTD___jmp_placeholder:
    JMP 0               // Line 2,3 (placeholder, gets replaced by KONESTD___jmp)

KONESTD___jmp:          // Jump to address R6,R7
    LDR 6
    STM 3
    LDR 7
    STR 3
    LDI 0b0000_0111
    AND 3
    STR 3
    LDM 2
    ORR 3
    STM 2
    JMP KONESTD___jmp_placeholder

KONESTD___ext:
    EXT

KONESTD___add_pc:
    ADD 6
    STR 6
    JC0 KONESTD___ext
    LDI 1
    ADD 7
    STR 7
    JMP KONESTD___ext

main:
    GPC
    LDI 50
    LDI 255
    STR 6
    JMP KONESTD___jmp
