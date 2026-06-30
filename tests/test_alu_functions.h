#ifndef TEST_ALU_FUNCTIONS_H
#define TEST_ALU_FUNCTIONS_H

#include <assert.h>
#include <stdio.h>

#include "../src/alu_functions.h"
#include "../src/cpu_functions.h"
#include "../src/cpu_struct.h"
#include "../src/utility.h"

void test_alu_not(CPU *cpu, Args *args);
void test_alu_bsl(CPU *cpu, Args *args);
void test_alu_bsr(CPU *cpu, Args *args);
void test_alu_brl(CPU *cpu, Args *args);
void test_alu_brr(CPU *cpu, Args *args);
void test_alu_ldi(CPU *cpu, Args *args);
void test_alu_ldr_str(CPU *cpu, Args *args);
void test_alu_orr(CPU *cpu, Args *args);
void test_alu_and(CPU *cpu, Args *args);
void test_alu_xor(CPU *cpu, Args *args);
void test_alu_add(CPU *cpu, Args *args);
void test_alu_ldm_stm(CPU *cpu, Args *args);
void test_alu_psh_pop(CPU *cpu, Args *args);
void test_alu_jmp(CPU *cpu, Args *args);
void test_alu_jc0_jc1(CPU *cpu, Args *args);
void test_alu_ja0_ja1(CPU *cpu, Args *args);
void test_alu_cll_ret(CPU *cpu, Args *args);

#endif
