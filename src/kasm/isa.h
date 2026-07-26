#ifndef ISA_H
#define ISA_H

#include <stdint.h>

// Operand class of an instruction; determines operand size and value range.
typedef enum {
    ARG_NONE, // no operand                          -> 1 byte  total
    ARG_REG,  // 5-bit register operand              -> 2 bytes total
    ARG_IMM,  // 8-bit immediate operand             -> 2 bytes total
    ARG_MEM,  // 16-bit memory/address operand (LE)  -> 3 bytes total
} ArgKind;

typedef struct {
    const char *mnemonic;
    uint8_t opcode;
    ArgKind arg_kind;
    int takes_label; // operand may be an address alias (label)
} Instruction;

// Look up an instruction by mnemonic. Returns NULL if unknown.
const Instruction *isa_lookup(const char *mnemonic);

// Inclusive upper bound for an operand of the given kind.
uint16_t isa_arg_max(ArgKind kind);

// Number of bytes an instruction of the given kind emits (opcode + operand).
int isa_instr_size(ArgKind kind);

#endif
