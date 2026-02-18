#ifndef CPU_STRUCT_H
#define CPU_STRUCT_H

#include <stdint.h>
#include <stdbool.h>

#define REG_SIZE 16
#define MEM_SIZE 65536

typedef struct {
    uint8_t R[REG_SIZE]; // register
    uint8_t M[MEM_SIZE]; // memory

    uint8_t *IR[3]; // instruction register

    uint8_t *F; // flags (F7: 0, F6: 0, F5: 0, F4: 0, F3: 0, F2: 0, F1: 0, F0: CARRY)
    uint8_t *A; // accumulator
    uint8_t *I; // input buffer

    uint8_t *SP[2]; // stack pointer
} CPU;

#endif
