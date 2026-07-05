#ifndef ASSEMBLER_H
#define ASSEMBLER_H

#include <stddef.h>
#include <stdint.h>

// Assemble the kasm program rooted at input_path into kone machine code.
//
// Returns a freshly allocated byte buffer (caller frees) and writes its length
// to *out_len. On any syntax or I/O error a diagnostic is printed to stderr and
// the process exits with EXIT_FAILURE, mirroring the fail-fast style used
// elsewhere in the project.
uint8_t *assemble_file(const char *input_path, size_t *out_len);

#endif
