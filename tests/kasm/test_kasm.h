#ifndef TEST_KASM_H
#define TEST_KASM_H

#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

#include "../../src/kasm/assembler.h"
#include "../../src/kasm/isa.h"
#include "../test_common.h"

void test_isa_lookup_known_mnemonic();
void test_isa_lookup_unknown_mnemonic();
void test_isa_arg_max();
void test_isa_instr_size();
void test_assemble_no_operand_opcodes();
void test_assemble_immediate_operand();
void test_assemble_register_operand();
void test_assemble_memory_operand_little_endian();
void test_assemble_label_resolves_to_address();
void test_assemble_include();

#endif
