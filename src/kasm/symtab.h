#ifndef SYMTAB_H
#define SYMTAB_H

#include <stddef.h>
#include <stdint.h>

// Maps a label to its address, or a -D constant to its value.
typedef struct {
    char *name;
    uint16_t value;
} Symbol;

typedef struct {
    Symbol *items;
    size_t len;
    size_t cap;
} SymTab;

void symtab_init(SymTab *t);
void symtab_free(SymTab *t);

// Inserts or overwrites the value for name; copies name.
void symtab_put(SymTab *t, const char *name, uint16_t value);

// Writes the value for name to *out and returns 1, or 0 if not found.
int symtab_get(const SymTab *t, const char *name, uint16_t *out);

#endif
