#ifndef SYMTAB_H
#define SYMTAB_H

#include <stddef.h>
#include <stdint.h>

// A growable map from label name to program address, used to resolve address
// aliases (labels) into absolute 16-bit jump/call targets.
typedef struct {
    char *name;
    uint16_t addr;
} Symbol;

typedef struct {
    Symbol *items;
    size_t len;
    size_t cap;
} SymTab;

void symtab_init(SymTab *t);
void symtab_free(SymTab *t);

// Insert or overwrite the address bound to name. Copies name.
void symtab_put(SymTab *t, const char *name, uint16_t addr);

// Look name up. On success writes the address to *out and returns 1; otherwise
// returns 0.
int symtab_get(const SymTab *t, const char *name, uint16_t *out);

#endif
