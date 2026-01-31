#ifndef CPU_FUNCTIONS_H
#define CPU_FUNCTIONS_H

#define NOP 0b00000000
#define NOT 0b00001000

#define LDR 0b00010000
#define STR 0b00011000
#define LDM 0b10010000
#define STM 0b10011000
#define LDI 0b10001000

#define ORR 0b00100000
#define AND 0b00101000
#define XOR 0b00110000
#define ADD 0b00111000

#define BSL 0b01000000
#define BSR 0b01001000
#define BRL 0b01010000
#define BRR 0b01011000

#define JMP 0b10100000
#define JC0 0b10101000
#define JC1 0b10110000
#define JA0 0b11101000
#define JA1 0b11110000

#include "alu_functions.h"
#include "cpu_struct.h"

#include <string.h>

void cpu_reset(CPU *cpu);
void cpu_fetch(CPU *cpu);
void cpu_decode_exec(CPU *cpu);

#endif
