#ifndef UTILITY_H
#define UTILITY_H

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int print_usage(char *argv[]);
int scanf_uint8(uint8_t *out);
uint8_t brl8(uint8_t x, unsigned n);
uint8_t brr8(uint8_t x, unsigned n);

#endif
