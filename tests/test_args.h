#include <assert.h>
#include <string.h>

#include "../src/args.h"
#include "test_common.h"

void test_args_defaults();
void test_args_bootfile();
void test_args_clockspeed();
void test_args_log();
void test_args_verbose_stacked();
void test_args_verbose_explicit();
void test_args_verbose_clamped();
void test_args_missing_bootfile_exits();
