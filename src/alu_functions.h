#ifndef ALU_FUNCTIONS_H
#define ALU_FUNCTIONS_H

#define FLAG_POS_CARRY 0

#include <stddef.h>

#include "cpu_struct.h"

// Operations with no argument:
void alu_not(CPU *cpu, char *msg, size_t msg_size);
void alu_bsl(CPU *cpu, char *msg, size_t msg_size);
void alu_bsr(CPU *cpu, char *msg, size_t msg_size);
void alu_brl(CPU *cpu, char *msg, size_t msg_size);
void alu_brr(CPU *cpu, char *msg, size_t msg_size);
void alu_psh(CPU *cpu, char *msg, size_t msg_size);
void alu_pop(CPU *cpu, char *msg, size_t msg_size);
void alu_ret(CPU *cpu, char *msg, size_t msg_size);
void alu_dsh(CPU *cpu, char *msg, size_t msg_size);
void alu_dop(CPU *cpu, char *msg, size_t msg_size);

// Operations with 'register' argument:
void alu_ldr(CPU *cpu, char *msg, size_t msg_size);
void alu_str(CPU *cpu, char *msg, size_t msg_size);
void alu_orr(CPU *cpu, char *msg, size_t msg_size);
void alu_and(CPU *cpu, char *msg, size_t msg_size);
void alu_xor(CPU *cpu, char *msg, size_t msg_size);
void alu_add(CPU *cpu, char *msg, size_t msg_size);

// Operations with 'immediate' argument:
void alu_ldi(CPU *cpu, char *msg, size_t msg_size);

// Operations with 'memory' argument:
void alu_ldm(CPU *cpu, char *msg, size_t msg_size);
void alu_stm(CPU *cpu, char *msg, size_t msg_size);
void alu_jmp(CPU *cpu, char *msg, size_t msg_size);
void alu_jc0(CPU *cpu, char *msg, size_t msg_size);
void alu_jc1(CPU *cpu, char *msg, size_t msg_size);
void alu_ja0(CPU *cpu, char *msg, size_t msg_size);
void alu_ja1(CPU *cpu, char *msg, size_t msg_size);
void alu_cll(CPU *cpu, char *msg, size_t msg_size);

#endif
