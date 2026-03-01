#include "utility.h"

void print_usage(char *argv[]) {
    fprintf(stderr, "Usage: %s -b BOOTFILE [-v[v[v]]] [-t MSEC]\n", 
            basename(argv[0]));
    exit(EXIT_FAILURE);
}

void parse_args(Args *args, int argc, char *argv[]) {
    args->bootfile = NULL;
    args->cycle_sleep = 1; // [ms]
    args->v = 0;
    int opt;
    int found = 0;

    while ((opt = getopt(argc, argv, "b:t:v")) != -1) {
        switch (opt) {
        case 'b':
            args->bootfile = optarg;
            found++;
            break;
        case 't':
            args->cycle_sleep = strtoul(optarg, NULL, 10);
            break;
        case 'v':
            args->v++;
            break;
        default:
            print_usage(argv);
        }
    }
    if (found < 1) print_usage(argv);
}

void addr_convert_8_to_16(uint16_t *addr16, const uint8_t addr8[2]) {
    *addr16 = ((uint16_t)addr8[1] << (8 * sizeof(uint8_t))) | (uint16_t)addr8[0];
}

void addr_convert_16_to_8(uint8_t addr8[2], uint16_t addr16) {
    addr8[0] = (uint8_t)(addr16 & 0xFF);
    addr8[1] = (uint8_t)(addr16 >> (8 * sizeof(uint8_t)));
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

// Searches byte from left (7) to right (0) and returns position of first '1' found:
int get_pos_first_1_in_byte(const uint8_t byte) {
    for (int pos = 7; pos >= 0; pos--) {
        if ((byte >> pos) & 0b00000001) {
            return pos;
        }
    }
    return -1;
}
