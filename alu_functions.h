#ifndef ALU_FUNCTIONS_H
#define ALU_FUNCTIONS_H

#include <stdio.h>
#include <stdlib.h>

#include "cpu_struct.h"
#include "utility.h"

void alu_ldr(CPU *cpu); 
void alu_str(CPU *cpu);
void alu_ldm(CPU *cpu);
void alu_stm(CPU *cpu);
void alu_ldi(CPU *cpu);
void alu_orr(CPU *cpu);
void alu_and(CPU *cpu);
void alu_xor(CPU *cpu);
void alu_not(CPU *cpu);
void alu_add(CPU *cpu);
void alu_bsl(CPU *cpu);
void alu_bsr(CPU *cpu);
void alu_brl(CPU *cpu);
void alu_brr(CPU *cpu);
void alu_jmp(CPU *cpu);
void alu_jc0(CPU *cpu);
void alu_jc1(CPU *cpu);
void alu_ja0(CPU *cpu);
void alu_ja1(CPU *cpu);
void alu_gpc(CPU *cpu);
void alu_out(CPU *cpu);
void alu_inn(CPU *cpu);
void alu_ext(CPU *cpu);

#endif
