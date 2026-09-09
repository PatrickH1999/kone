#ifndef TEST_CPU_FUNCTIONS_H
#define TEST_CPU_FUNCTIONS_H

#include <assert.h>

#include "../src/kone/cpu_functions.h"
#include "../src/kone/utility.h"
#include "test_common.h"

void test_cpu_init(CPU *cpu);
void test_cpu_reset(CPU *cpu);
void test_cpu_get_flag(CPU *cpu);
void test_cpu_set_flag(CPU *cpu);

#endif
