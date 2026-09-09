#ifndef ALU_FUNCTIONS_H
#define ALU_FUNCTIONS_H

#define FLAG_POS_CARRY 0

#include <stddef.h>

#include "cpu_struct.h"

// Operations with no argument:
void alu_not(const CPU *cpu, char *msg, size_t msg_size);
void alu_bsl(const CPU *cpu, char *msg, size_t msg_size);
void alu_bsr(const CPU *cpu, char *msg, size_t msg_size);
void alu_brl(const CPU *cpu, char *msg, size_t msg_size);
void alu_brr(const CPU *cpu, char *msg, size_t msg_size);
void alu_psh(CPU *cpu, char *msg, size_t msg_size);
void alu_pop(CPU *cpu, char *msg, size_t msg_size);
void alu_ret(CPU *cpu, char *msg, size_t msg_size);

// Operations with 'register' argument:
void alu_ldr(const CPU *cpu, char *msg, size_t msg_size);
void alu_str(CPU *cpu, char *msg, size_t msg_size);
void alu_orr(const CPU *cpu, char *msg, size_t msg_size);
void alu_and(const CPU *cpu, char *msg, size_t msg_size);
void alu_xor(const CPU *cpu, char *msg, size_t msg_size);
void alu_add(const CPU *cpu, char *msg, size_t msg_size);

// Operations with 'immediate' argument:
void alu_ldi(const CPU *cpu, char *msg, size_t msg_size);

// Operations with 'memory' argument:
void alu_ldm(const CPU *cpu, char *msg, size_t msg_size);
void alu_stm(CPU *cpu, char *msg, size_t msg_size);
void alu_jmp(const CPU *cpu, char *msg, size_t msg_size);
void alu_jc0(const CPU *cpu, char *msg, size_t msg_size);
void alu_jc1(const CPU *cpu, char *msg, size_t msg_size);
void alu_ja0(const CPU *cpu, char *msg, size_t msg_size);
void alu_ja1(const CPU *cpu, char *msg, size_t msg_size);
void alu_cll(CPU *cpu, char *msg, size_t msg_size);

#endif
