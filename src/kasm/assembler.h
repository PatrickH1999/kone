#ifndef ASSEMBLER_H
#define ASSEMBLER_H

#include <stddef.h>
#include <stdint.h>

#include "symtab.h"

// Adds NAME=VALUE to constants. Returns 0, adding nothing, if def is malformed,
// NAME reads as a number or is already defined, or VALUE exceeds 16 bits.
int assembler_define(SymTab *constants, const char *def);

// Returns a freshly allocated buffer (caller frees) and writes its length to
// *out_len; exits the process on any syntax or I/O error. A constant stands in
// for a literal wherever one is allowed.
uint8_t *assemble_file(const char *input_path, const SymTab *constants,
                       size_t *out_len);

#endif
