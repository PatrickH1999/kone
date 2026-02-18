#ifndef UTILITY_H
#define UTILITY_H

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int print_usage(char *argv[]);
static inline void addr_convert_8_to_16(uint16_t *addr16, const uint8_t addr8[2]);
static inline void addr_convert_16_to_8(uint8_t addr8[2], uint16_t addr16);
int scanf_uint8(uint8_t *out);
uint8_t brl8(uint8_t x, unsigned n);
uint8_t brr8(uint8_t x, unsigned n);

#endif
