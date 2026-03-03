#ifndef UTILITY_H
#define UTILITY_H

#include <errno.h>
#include <libgen.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

typedef struct {
    const char *bootfile;     // bootfile
    unsigned int cycle_sleep; // sleep time between clock cycles [ms]
    int v;                    // verbosity
} Args;

void parse_args(Args *args, int argc, char *argv[]);
void print_usage(char *argv[]);
void addr_convert_8_to_16(uint16_t *addr16, const uint8_t addr8[2]);
void addr_convert_16_to_8(uint8_t addr8[2], uint16_t addr16);
int scanf_uint8(uint8_t *out);
uint8_t brl8(uint8_t x, unsigned n);
uint8_t brr8(uint8_t x, unsigned n);
int get_pos_first_1_in_byte(uint8_t byte);
void print_bin(uint8_t x);

#endif
