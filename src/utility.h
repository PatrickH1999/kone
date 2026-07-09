#ifndef UTILITY_H
#define UTILITY_H

#include <errno.h>
#include <signal.h>

#include "cpu_struct.h"
#include "cpu_functions.h"
#include "display_struct.h"
#include "display_functions.h"

void print_out(CPU *cpu, Display *display, int v);
void out_cleanup(int sig);
void addr_convert_8_to_16(uint16_t *addr16, const uint8_t addr8[2]);
void addr_convert_16_to_8(uint8_t addr8[2], uint16_t addr16);
int scanf_uint8(uint8_t *out);
uint8_t brl8(uint8_t x, unsigned n);
uint8_t brr8(uint8_t x, unsigned n);
int get_pos_first_1_in_byte(uint8_t byte);
void print_bin(uint8_t x);

#endif
