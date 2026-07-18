#ifndef ALU_FUNCTIONS_H
#define ALU_FUNCTIONS_H

#define FLAG_POS_CARRY 0

#include "args.h"
#include "cpu_struct.h"

// Operations with no argument:
char *alu_not(CPU *cpu);
char *alu_bsl(CPU *cpu);
char *alu_bsr(CPU *cpu);
char *alu_brl(CPU *cpu);
char *alu_brr(CPU *cpu);
char *alu_psh(CPU *cpu);
char *alu_pop(CPU *cpu);
char *alu_ret(CPU *cpu);
char *alu_dsh(CPU *cpu);
char *alu_dop(CPU *cpu);

// Operations with 'register' argument:
char *alu_ldr(CPU *cpu);
char *alu_str(CPU *cpu);
char *alu_orr(CPU *cpu);
char *alu_and(CPU *cpu);
char *alu_xor(CPU *cpu);
char *alu_add(CPU *cpu);

// Operations with 'immediate' argument:
char *alu_ldi(CPU *cpu);

// Operations with 'memory' argument:
char *alu_ldm(CPU *cpu);
char *alu_stm(CPU *cpu);
char *alu_jmp(CPU *cpu);
char *alu_jc0(CPU *cpu);
char *alu_jc1(CPU *cpu);
char *alu_ja0(CPU *cpu);
char *alu_ja1(CPU *cpu);
char *alu_cll(CPU *cpu);

#endif
