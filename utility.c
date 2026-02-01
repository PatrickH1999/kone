#include "utility.h"

int print_usage(char *argv[]) {
    fprintf(stderr, "Usage: %s <bootfile>.bin\n", argv[0]);
    return 1;
}

int scanf_uint8(uint8_t *out) {
    char buf[32];
    char *end;
    unsigned long tmp;

    if (!out) 
        return 0;

    if (!fgets(buf, sizeof buf, stdin))
        return 0;

    errno = 0;
    tmp = strtoul(buf, &end, 10);

    if (end == buf)
        return 0;

    if (*end != '\n' && *end != '\0')
        return 0;

    if (errno || tmp > UINT8_MAX)
        return 0;

    *out = (uint8_t)tmp;
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
