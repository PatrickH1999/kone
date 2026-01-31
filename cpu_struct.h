#ifndef CPU_STRUCT_H
#define CPU_STRUCT_H

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    uint8_t B;   // bus
    uint8_t A;   // accumulator
    uint8_t I;   // input buffer
    uint8_t R[8];   // register
    uint8_t M[2048];   // memory
    uint16_t PC;   // program counter
    bool C;   // carry
    uint8_t IR0;   // instruction register (cycle 0)
    uint8_t IR1;   // instruction register (cycle 1)
} CPU;

#endif
