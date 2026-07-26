#ifndef TEST_DISPLAY_FUNCTIONS_H
#define TEST_DISPLAY_FUNCTIONS_H

#include <assert.h>
#include <stdio.h>

#include "../src/display_functions.h"
#include "../src/cpu_functions.h"
#include "test_common.h"

void test_display_reset();
void test_display_push_char_basic();
void test_display_push_char_col_wrap();
void test_display_push_char_row_wrap();
void test_display_fetch_set();
void test_display_fetch_no_set();

#endif
