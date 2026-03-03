#ifndef ALU_FUNCTIONS_H
#define ALU_FUNCTIONS_H

#define FLAG_POS_CARRY 0

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "cpu_functions.h"
#include "cpu_struct.h"
#include "utility.h"

void alu_not(CPU *cpu, Args *args);
void alu_bsl(CPU *cpu, Args *args);
void alu_bsr(CPU *cpu, Args *args);
void alu_brl(CPU *cpu, Args *args);
void alu_brr(CPU *cpu, Args *args);
void alu_psh(CPU *cpu, Args *args);
void alu_pop(CPU *cpu, Args *args);
void alu_ret(CPU *cpu, Args *args);
void alu_ldr(CPU *cpu, Args *args);
void alu_str(CPU *cpu, Args *args);
void alu_orr(CPU *cpu, Args *args);
void alu_and(CPU *cpu, Args *args);
void alu_xor(CPU *cpu, Args *args);
void alu_add(CPU *cpu, Args *args);
void alu_ldi(CPU *cpu, Args *args);
void alu_ldm(CPU *cpu, Args *args);
void alu_stm(CPU *cpu, Args *args);
void alu_jmp(CPU *cpu, Args *args);
void alu_jc0(CPU *cpu, Args *args);
void alu_jc1(CPU *cpu, Args *args);
void alu_ja0(CPU *cpu, Args *args);
void alu_ja1(CPU *cpu, Args *args);
void alu_cll(CPU *cpu, Args *args);

#endif
