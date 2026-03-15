#ifndef CPU_FUNCTIONS_H
#define CPU_FUNCTIONS_H

#define OC_FLAG_POS_R 7 // opcode flag: argument is register
#define OC_FLAG_POS_I 6 // opcode flag: argument is immediate
#define OC_FLAG_POS_M 5 // opcode flag: argument is memory address
#define OC_FLAG_POS_V 4 // opcode flag: virtual opcode

#define NOP 0b00000000
#define NOT 0b00000001
#define BSL 0b00000100
#define BSR 0b00000101
#define BRL 0b00000110
#define BRR 0b00000111
#define PSH 0b00001000
#define POP 0b00001001
#define RET 0b00001010

#define LDR 0b10000000
#define STR 0b10010000
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

#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

#include "alu_functions.h"
#include "cpu_struct.h"
#include "utility.h"

void cpu_reset(CPU *cpu);
int cpu_boot_file(CPU *cpu, const char *path);
void cpu_pc_increment(CPU *cpu, Args *args);
void cpu_fetch(CPU *cpu, Args *args);
void cpu_decode_exec(CPU *cpu, Args *args);
uint8_t cpu_get_flag(CPU *cpu, uint8_t flag_pos);
void cpu_set_flag(CPU *cpu, uint8_t flag_pos, uint8_t value);
void cpu_print_state(CPU *cpu);
void cpu_print_d(CPU *cpu);

#endif
