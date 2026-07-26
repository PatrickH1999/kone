#ifndef TEST_KEYBOARD_FUNCTIONS_H
#define TEST_KEYBOARD_FUNCTIONS_H

#include <assert.h>
#include <stdio.h>
#include <unistd.h>

#include "../src/cpu_functions.h"
#include "../src/keyboard_functions.h"
#include "test_common.h"

void test_keyboard_get_char_reads_available_byte();
void test_keyboard_get_char_returns_neg1_when_no_input();
void test_keyboard_push_cpu_sets_char_in_range();
void test_keyboard_push_cpu_replaces_out_of_range_char();
void test_keyboard_push_cpu_no_input_leaves_registers_unset();

#endif
