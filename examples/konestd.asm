start:
    JMP main

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
    JMP KONESTD___add_pc
