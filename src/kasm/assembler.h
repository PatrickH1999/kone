#ifndef ASSEMBLER_H
#define ASSEMBLER_H

#include <stddef.h>
#include <stdint.h>

// Returns a freshly allocated buffer (caller frees) and writes its length to
// *out_len; exits the process on any syntax or I/O error.
uint8_t *assemble_file(const char *input_path, size_t *out_len);

#endif
