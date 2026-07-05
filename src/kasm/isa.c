#include "isa.h"

#include <string.h>

// The kone instruction set. Opcodes and operand classes follow the encoding
// described in README.md ("Instruction Set"). Labels are only meaningful for
// control-flow targets, so only those instructions set takes_label.
static const Instruction ISA[] = {
    // no operand
    {"NOP", 0x00, ARG_NONE, 0},
    {"NOT", 0x01, ARG_NONE, 0},
    {"BSL", 0x04, ARG_NONE, 0},
    {"BSR", 0x05, ARG_NONE, 0},
    {"BRL", 0x06, ARG_NONE, 0},
    {"BRR", 0x07, ARG_NONE, 0},
    {"PSH", 0x08, ARG_NONE, 0},
    {"POP", 0x09, ARG_NONE, 0},
    {"RET", 0x0A, ARG_NONE, 0},
    // register operand
    {"LDR", 0x80, ARG_REG, 0},
    {"STR", 0x90, ARG_REG, 0},
    {"ORR", 0xC0, ARG_REG, 0},
    {"AND", 0xD0, ARG_REG, 0},
    {"XOR", 0xE0, ARG_REG, 0},
    {"ADD", 0xF0, ARG_REG, 0},
    // immediate operand
    {"LDI", 0x40, ARG_IMM, 0},
    // memory / address operand
    {"LDM", 0x20, ARG_MEM, 0},
    {"STM", 0x21, ARG_MEM, 0},
    {"JMP", 0x28, ARG_MEM, 1},
    {"JC0", 0x29, ARG_MEM, 1},
    {"JC1", 0x2A, ARG_MEM, 1},
    {"JA0", 0x2C, ARG_MEM, 1},
    {"JA1", 0x2D, ARG_MEM, 1},
    {"CLL", 0x30, ARG_MEM, 1},
};

static const size_t ISA_COUNT = sizeof ISA / sizeof ISA[0];

const Instruction *isa_lookup(const char *mnemonic) {
    for (size_t i = 0; i < ISA_COUNT; i++) {
        if (strcmp(ISA[i].mnemonic, mnemonic) == 0) return &ISA[i];
    }
    return NULL;
}

uint16_t isa_arg_max(ArgKind kind) {
    switch (kind) {
    case ARG_REG:
        return 0x000F;
    case ARG_IMM:
        return 0x00FF;
    case ARG_MEM:
        return 0xFFFF;
    case ARG_NONE:
        return 0;
    }
    return 0;
}

int isa_instr_size(ArgKind kind) {
    switch (kind) {
    case ARG_NONE:
        return 1;
    case ARG_REG:
        return 2;
    case ARG_IMM:
        return 2;
    case ARG_MEM:
        return 3;
    }
    return 0;
}
