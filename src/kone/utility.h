#ifndef UTILITY_H
#define UTILITY_H

#include <stdint.h>

#include "args.h"
#include "cpu_struct.h"
#include "display_struct.h"

void print_out(const CPU *cpu, const char *cpu_msg, const Display *display,
               const Args *args);
void out_cleanup(int sig);
void sleep_ns(long ns);
void addr_convert_8_to_16(uint16_t *addr16, const uint8_t addr8[2]);
void addr_convert_16_to_8(uint8_t addr8[2], uint16_t addr16);
uint8_t brl8(uint8_t x, unsigned n);
uint8_t brr8(uint8_t x, unsigned n);
int get_pos_first_1_in_byte(uint8_t byte);
void print_bin(uint8_t x);

#endif
