#ifndef TEST_ALU_FUNCTIONS_H
#define TEST_ALU_FUNCTIONS_H

#include <assert.h>
#include <stdio.h>

#include "../src/cpu_functions.h"
#include "../src/alu_functions.h"

int main();
void test_alu_not();
void test_alu_bsl();
void test_alu_bsr();
void test_alu_brl();
void test_alu_brr();
void test_alu_ldi();
void test_alu_ldr_str();
void test_alu_orr();
void test_alu_and();
void test_alu_xor();
void test_alu_add();
void test_alu_ldm_stm();
void test_alu_psh_pop();
void test_alu_jmp();
void test_alu_jc0_jc1();
void test_alu_ja0_ja1();
void test_alu_cll_ret();

#endif
