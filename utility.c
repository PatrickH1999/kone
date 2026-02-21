#include "utility.h"

int print_usage(char *argv[]) {
    fprintf(stderr, "Usage: %s <bootfile>.bin\n", argv[0]);
    return 1;
}

void addr_convert_8_to_16(uint16_t *addr16, const uint8_t addr8[2]) {
    *addr16 = ((uint16_t)addr8[1] << 8) | addr8[0];
}

void addr_convert_16_to_8(uint8_t addr8[2], uint16_t addr16) {
    addr8[0] = addr16 & 0xFF;
    addr8[1] = addr16 >> 8;
}

int scanf_uint8(uint8_t *out) {
    char buf[32];
    char *end;
    unsigned long tmp;

    if (!out) return 0;

    if (!fgets(buf, sizeof buf, stdin)) return 0;

    errno = 0;
    tmp = strtoul(buf, &end, 10);

    if (end == buf) return 0;

    if (*end != '\n' && *end != '\0') return 0;

    if (errno || tmp > UINT8_MAX) return 0;

    *out = (uint8_t)tmp;
    return 1;
}

uint8_t brl8(uint8_t x, unsigned n) {
    n &= 7; // n mod 8
    return (x << n) | (x >> (8 - n));
}

uint8_t brr8(uint8_t x, unsigned n) {
    n &= 7; // n mod 8
    return (x >> n) | (x << (8 - n));
}
