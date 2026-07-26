#include "symtab.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *xstrdup(const char *s) {
    size_t n = strlen(s) + 1;
    char *p = malloc(n);
    if (!p) {
        perror("kasm: malloc");
        exit(EXIT_FAILURE);
    }
    memcpy(p, s, n);
    return p;
}

void symtab_init(SymTab *t) {
    t->items = NULL;
    t->len = 0;
    t->cap = 0;
}

void symtab_free(SymTab *t) {
    for (size_t i = 0; i < t->len; i++)
        free(t->items[i].name);
    free(t->items);
    symtab_init(t);
}

static Symbol *symtab_find(const SymTab *t, const char *name) {
    for (size_t i = 0; i < t->len; i++) {
        if (strcmp(t->items[i].name, name) == 0) return &t->items[i];
    }
    return NULL;
}

void symtab_put(SymTab *t, const char *name, uint16_t addr) {
    Symbol *existing = symtab_find(t, name);
    if (existing) {
        existing->addr = addr;
        return;
    }
    if (t->len == t->cap) {
        size_t cap = t->cap ? t->cap * 2 : 16;
        Symbol *items = realloc(t->items, cap * sizeof *items);
        if (!items) {
            perror("kasm: realloc");
            exit(EXIT_FAILURE);
        }
        t->items = items;
        t->cap = cap;
    }
    t->items[t->len].name = xstrdup(name);
    t->items[t->len].addr = addr;
    t->len++;
}

int symtab_get(const SymTab *t, const char *name, uint16_t *out) {
    Symbol *s = symtab_find(t, name);
    if (!s) return 0;
    *out = s->addr;
    return 1;
}
