#include "utility.h"

int print_usage(char *argv[]) {
    fprintf(stderr, "Usage: %s <bootfile>.bin\n", argv[0]);
    return 1;
}

uint8_t brl8(uint8_t x, unsigned n)
{
    n &= 7;  // n mod 8
    return (x << n) | (x >> (8 - n));
}

uint8_t brr8(uint8_t x, unsigned n)
{
    n &= 7;  // n mod 8
    return (x >> n) | (x << (8 - n));
}
