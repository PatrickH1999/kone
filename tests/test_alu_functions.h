#ifndef TEST_ALU_FUNCTIONS_H
#define TEST_ALU_FUNCTIONS_H

#include <assert.h>

#include "../src/kone/alu_functions.h"
#include "../src/kone/cpu_functions.h"
#include "../src/kone/utility.h"
#include "test_common.h"

void test_alu_not(CPU *cpu);
void test_alu_bsl(CPU *cpu);
void test_alu_bsr(CPU *cpu);
void test_alu_brl(CPU *cpu);
void test_alu_brr(CPU *cpu);
void test_alu_ldi(CPU *cpu);
void test_alu_ldr_str(CPU *cpu);
void test_alu_orr(CPU *cpu);
void test_alu_and(CPU *cpu);
void test_alu_xor(CPU *cpu);
void test_alu_add(CPU *cpu);
void test_alu_ldm_stm(CPU *cpu);
void test_alu_psh_pop(CPU *cpu);
void test_alu_jmp(CPU *cpu);
void test_alu_jc0_jc1(CPU *cpu);
void test_alu_ja0_ja1(CPU *cpu);
void test_alu_cll_ret(CPU *cpu);

#endif
