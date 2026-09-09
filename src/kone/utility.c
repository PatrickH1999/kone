#include "utility.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "cpu_functions.h"
#include "display_functions.h"

void print_out(const CPU *cpu, const char *cpu_msg, const Display *display,
               const Args *args) {
    if (!args->log) printf("\033[3J\033[H\033[2J"); // clear screen
    display_print(display);
    if (args->v > 0) cpu_print_count(cpu);
    if (args->v > 1) printf("\tExecuted: %s\n", cpu_msg);
    if (args->v > 2) cpu_print_state(cpu);
}

void out_cleanup(const int sig) {
    (void)sig;
    printf("\033[?25h\033[?1049l");
    fflush(stdout);
    exit(0);
}

void sleep_ns(const long ns) {
    const struct timespec ts = {.tv_sec = ns / 1000000000L,
                                .tv_nsec = ns % 1000000000L};
    nanosleep(&ts, NULL);
}

void addr_convert_8_to_16(uint16_t *addr16, const uint8_t addr8[2]) {
    *addr16 =
        ((uint16_t)addr8[1] << (8 * sizeof(uint8_t))) | (uint16_t)addr8[0];
}

void addr_convert_16_to_8(uint8_t addr8[2], const uint16_t addr16) {
    addr8[0] = (uint8_t)(addr16 & 0xFF);
    addr8[1] = (uint8_t)(addr16 >> (8 * sizeof(uint8_t)));
}

uint8_t brl8(const uint8_t x, unsigned n) {
    n &= 7; // n mod 8
    return (x << n) | (x >> (8 - n));
}

uint8_t brr8(const uint8_t x, unsigned n) {
    n &= 7; // n mod 8
    return (x >> n) | (x << (8 - n));
}

// Searches byte from left (7) to right (0) and returns position of first '1'
// found:
int get_pos_first_1_in_byte(const uint8_t byte) {
    for (int pos = 7; pos >= 0; pos--) {
        if ((byte >> pos) & 0b00000001) {
            return pos;
        }
    }
    return -1;
}

void print_bin(const uint8_t x) {
    for (int i = 7; i >= 0; i--) {
        printf("%d", (x >> i) & 1);
    }
}
