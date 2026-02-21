#ifndef CPU_FUNCTIONS_H
#define CPU_FUNCTIONS_H

#define _POSIX_C_SOURCE 199309L
#define CYCLE_SLEEP 1 // [ms]

#define NOP 0b00000000
#define NOT 0b00000001
#define BSL 0b00000100
#define BSR 0b00000101
#define BRL 0b00000110
#define BRR 0b00000111
#define RET 0b00001000

#define LDR 0b10000000
#define STR 0b10010000
#define PSH 0b10100000
#define POP 0b10110000
#define ORR 0b11000000
#define AND 0b11010000
#define XOR 0b11100000
#define ADD 0b11110000

#define LDI 0b01000000

#define LDM 0b00100000
#define STM 0b00100001
#define JMP 0b00101000
#define JC0 0b00101001
#define JC1 0b00101010
#define JA0 0b00101100
#define JA1 0b00101101
#define CLL 0b00110000

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

#include "alu_functions.h"
#include "cpu_struct.h"

void cpu_init(CPU *cpu);
int cpu_boot_file(CPU *cpu, const char *path);
void cpu_reset(CPU *cpu);
void cpu_fetch(CPU *cpu);
void cpu_decode_exec(CPU *cpu);

#endif
