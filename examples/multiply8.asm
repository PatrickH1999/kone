INN 0     // input left (R0)
INN 1     // input right (R1)
LDI 0
//
STR 2     // output (R2)
LDI 248
//
STR 3     // bit counter (starts at 248, ends at 0) (R3)
LDI 1     // LOOP
//
AND 1
JA0 16    // jump to CONTINUE (line 16) if first digit in R1 is 0, ELSE:
//
LDR 2
ADD 0
STR 2     // R2 = R2 + R0
LDR 0     // CONTINUE
BSL
STR 0     // R0 bitshift left (multiply by one order)
LDR 1
BSR
STR 1     // R1 bitshift right
LDI 1
//
ADD 3
STR 3     // R3 += 1
JA1 6     // jump to LOOP (line 8) if bit counter is not zero
OUT 2     // print result
EXT       // exit
