#include "assembler.h"

#include "isa.h"
#include "symtab.h"

#include <ctype.h>
#include <errno.h>
#include <libgen.h>
#include <limits.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

#define MAX_TOKENS 8
#define MAX_INCLUDE_DEPTH 64
#define ADDR_SPACE 65536 // 16-bit address space -> max program size in bytes

static void die(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    fputs("kasm: error: ", stderr);
    vfprintf(stderr, fmt, ap);
    fputc('\n', stderr);
    va_end(ap);
    exit(EXIT_FAILURE);
}

static void die_at(const char *file, int line, const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    fprintf(stderr, "kasm: %s:%d: error: ", file, line);
    vfprintf(stderr, fmt, ap);
    fputc('\n', stderr);
    va_end(ap);
    exit(EXIT_FAILURE);
}

static void *xmalloc(size_t n) {
    void *p = malloc(n);
    if (!p) die("out of memory");
    return p;
}

static char *xstrdup(const char *s) {
    size_t n = strlen(s) + 1;
    char *p = xmalloc(n);
    memcpy(p, s, n);
    return p;
}

// Each line keeps its origin so error messages can point back to it.
typedef struct {
    char *text; // line contents, newline stripped
    char *file; // originating file (for diagnostics)
    int lineno; // 1-based line number within that file
} SourceLine;

typedef struct {
    SourceLine *items;
    size_t len;
    size_t cap;
} LineList;

static void lines_init(LineList *l) {
    l->items = NULL;
    l->len = 0;
    l->cap = 0;
}

static void lines_free(LineList *l) {
    for (size_t i = 0; i < l->len; i++) {
        free(l->items[i].text);
        free(l->items[i].file);
    }
    free(l->items);
    lines_init(l);
}

static void lines_push(LineList *l, const char *text, const char *file,
                       int lineno) {
    if (l->len == l->cap) {
        l->cap = l->cap ? l->cap * 2 : 256;
        l->items = realloc(l->items, l->cap * sizeof *l->items);
        if (!l->items) die("out of memory");
    }
    l->items[l->len].text = xstrdup(text);
    l->items[l->len].file = xstrdup(file);
    l->items[l->len].lineno = lineno;
    l->len++;
}

// Splits buf on whitespace into tok[], stopping at a "//" comment. Mutates
// buf in place; tok[] entries alias into it.
static int tokenize(char *buf, char *tok[MAX_TOKENS]) {
    int n = 0;
    char *p = buf;
    while (*p) {
        while (*p && isspace((unsigned char)*p))
            p++;
        if (!*p) break;
        char *start = p;
        while (*p && !isspace((unsigned char)*p))
            p++;
        if (*p) *p++ = '\0';
        if (start[0] == '/' && start[1] == '/') break; // comment starts here
        if (n < MAX_TOKENS) tok[n] = start;
        n++;
    }
    return n;
}

// Accepts decimal or 0x/0b/0o literals; returns 1 on success, 0 otherwise.
static int parse_uint(const char *s, long *out) {
    int base = 10;
    if (s[0] == '0' && (s[1] == 'x' || s[1] == 'X'))
        base = 16, s += 2;
    else if (s[0] == '0' && (s[1] == 'b' || s[1] == 'B'))
        base = 2, s += 2;
    else if (s[0] == '0' && (s[1] == 'o' || s[1] == 'O'))
        base = 8, s += 2;
    if (*s == '\0') return 0;

    errno = 0;
    char *end;
    long v = strtol(s, &end, base);
    if (*end != '\0' || errno || v < 0) return 0;
    *out = v;
    return 1;
}

typedef struct {
    char *paths[MAX_INCLUDE_DEPTH]; // canonical paths of the include chain
    int depth;
} IncludeStack;

static void load_source(const char *path, LineList *out, IncludeStack *stack);

// Resolve an include path relative to the directory of the including file.
static char *resolve_include(const char *including_file, const char *target) {
    char *dir_copy = xstrdup(including_file);
    const char *dir = dirname(dir_copy);
    size_t n = strlen(dir) + 1 + strlen(target) + 1;
    char *joined = xmalloc(n);
    snprintf(joined, n, "%s/%s", dir, target);
    free(dir_copy);
    return joined;
}

static char *strip_quotes(char *s) {
    size_t n = strlen(s);
    if (n >= 2 && s[0] == '"' && s[n - 1] == '"') {
        s[n - 1] = '\0';
        return s + 1;
    }
    return s;
}

static void handle_include(const char *including_file, int lineno,
                           char *tok[MAX_TOKENS], int ntok, LineList *out,
                           IncludeStack *stack) {
    if (ntok != 2)
        die_at(including_file, lineno,
               "'.include' expects exactly one file argument");
    char *target = strip_quotes(tok[1]);
    char *inc_path = resolve_include(including_file, target);
    load_source(inc_path, out, stack);
    free(inc_path);
}

static void load_source(const char *path, LineList *out, IncludeStack *stack) {
    FILE *f = fopen(path, "r");
    if (!f) die("cannot open '%s': %s", path, strerror(errno));

    // realpath() is only for canonicalizing paths in circular-include
    // detection; fall back to the raw path if it fails (e.g. FUSE mounts).
    char canon[PATH_MAX];
    const char *canon_path = realpath(path, canon) ? canon : path;

    for (int i = 0; i < stack->depth; i++)
        if (strcmp(stack->paths[i], canon_path) == 0)
            die("circular include detected: '%s'", path);

    if (stack->depth >= MAX_INCLUDE_DEPTH)
        die("include nesting too deep (limit %d)", MAX_INCLUDE_DEPTH);

    stack->paths[stack->depth++] = xstrdup(canon_path);

    char *raw = NULL;
    size_t cap = 0;
    ssize_t len;
    int lineno = 0;
    while ((len = getline(&raw, &cap, f)) != -1) {
        lineno++;
        while (len > 0 && (raw[len - 1] == '\n' || raw[len - 1] == '\r'))
            raw[--len] = '\0';

        char *scratch = xstrdup(raw);
        char *tok[MAX_TOKENS];
        int ntok = tokenize(scratch, tok);

        if (ntok > 0 && strcmp(tok[0], ".include") == 0)
            handle_include(path, lineno, tok, ntok, out, stack);
        else
            lines_push(out, raw, path, lineno);

        free(scratch);
    }
    free(raw);
    fclose(f);

    free(stack->paths[--stack->depth]);
}

typedef struct {
    uint8_t *data;
    size_t len;
    size_t cap;
} ByteBuf;

static void bytes_init(ByteBuf *b) {
    b->data = NULL;
    b->len = 0;
    b->cap = 0;
}

static void bytes_push(ByteBuf *b, uint8_t x) {
    if (b->len == b->cap) {
        b->cap = b->cap ? b->cap * 2 : 256;
        b->data = realloc(b->data, b->cap);
        if (!b->data) die("out of memory");
    }
    b->data[b->len++] = x;
}

// Splits tok[] into leading labels and the rest of the line, defining each
// label at pc when define is set. Returns the index of the instruction, or
// ntok if the line holds only labels.
static int process_labels(char *tok[MAX_TOKENS], int ntok, uint16_t pc,
                          SymTab *symbols, int define, const SourceLine *ln) {
    int i = 0;
    while (i < ntok) {
        size_t wlen = strlen(tok[i]);
        if (wlen == 0 || tok[i][wlen - 1] != ':') break; // not a label
        if (wlen == 1) die_at(ln->file, ln->lineno, "empty label name");
        if (define) {
            tok[i][wlen - 1] = '\0'; // drop trailing ':'
            symtab_put(symbols, tok[i], pc);
        }
        i++;
    }
    return i;
}

static uint16_t resolve_operand(const Instruction *instr, const char *operand,
                                const SymTab *symbols, const SourceLine *ln) {
    long value;
    if (parse_uint(operand, &value)) {
        if (value > isa_arg_max(instr->arg_kind))
            die_at(ln->file, ln->lineno,
                   "operand %ld out of range for %s (max %u)", value,
                   instr->mnemonic, isa_arg_max(instr->arg_kind));
        return (uint16_t)value;
    }

    uint16_t addr;
    if (symtab_get(symbols, operand, &addr)) {
        if (!instr->takes_label)
            die_at(ln->file, ln->lineno,
                   "%s does not accept a label operand ('%s')", instr->mnemonic,
                   operand);
        return addr;
    }

    die_at(ln->file, ln->lineno,
           "operand '%s' is neither a valid integer nor a known label",
           operand);
    return 0; // unreachable
}

// Validates operand count for tok[first..]; encodes into out when emit is
// set. Returns the instruction's size in bytes.
static int encode_instruction(char *tok[MAX_TOKENS], int first, int ntok,
                              const SymTab *symbols, const SourceLine *ln,
                              int emit, ByteBuf *out) {
    const Instruction *instr = isa_lookup(tok[first]);
    if (!instr) die_at(ln->file, ln->lineno, "unknown opcode '%s'", tok[first]);

    int nargs = ntok - first - 1;
    int expected = (instr->arg_kind == ARG_NONE) ? 0 : 1;
    if (nargs != expected)
        die_at(ln->file, ln->lineno, "%s expects %d operand%s, got %d",
               instr->mnemonic, expected, expected == 1 ? "" : "s", nargs);

    if (emit) {
        bytes_push(out, instr->opcode);
        if (instr->arg_kind != ARG_NONE) {
            uint16_t v = resolve_operand(instr, tok[first + 1], symbols, ln);
            switch (instr->arg_kind) {
            case ARG_REG:
            case ARG_IMM:
                bytes_push(out, (uint8_t)v);
                break;
            case ARG_MEM:
                bytes_push(out, (uint8_t)(v & 0xFF));        // low byte
                bytes_push(out, (uint8_t)((v >> 8) & 0xFF)); // high byte
                break;
            case ARG_NONE:
                break;
            }
        }
    }
    return isa_instr_size(instr->arg_kind);
}

uint8_t *assemble_file(const char *input_path, size_t *out_len) {
    LineList lines;
    lines_init(&lines);
    IncludeStack stack = {.depth = 0};
    load_source(input_path, &lines, &stack);

    SymTab symbols;
    symtab_init(&symbols);

    // Pass 1: assign an address to every label.
    uint32_t pc = 0;
    for (size_t i = 0; i < lines.len; i++) {
        const SourceLine *ln = &lines.items[i];
        char *scratch = xstrdup(ln->text);
        char *tok[MAX_TOKENS];
        int ntok = tokenize(scratch, tok);

        if (ntok > MAX_TOKENS)
            die_at(ln->file, ln->lineno, "more than %d tokens on one line",
                   MAX_TOKENS);
        int first = process_labels(tok, ntok, (uint16_t)pc, &symbols, 1, ln);
        if (first < ntok)
            pc += encode_instruction(tok, first, ntok, &symbols, ln, 0, NULL);
        if (pc > ADDR_SPACE)
            die_at(ln->file, ln->lineno,
                   "program exceeds %d-byte address space", ADDR_SPACE);
        free(scratch);
    }

    // Pass 2: emit machine code now that all labels are known.
    ByteBuf out;
    bytes_init(&out);
    for (size_t i = 0; i < lines.len; i++) {
        const SourceLine *ln = &lines.items[i];
        char *scratch = xstrdup(ln->text);
        char *tok[MAX_TOKENS];
        int ntok = tokenize(scratch, tok);

        int first = process_labels(tok, ntok, 0, &symbols, 0, ln);
        if (first < ntok)
            encode_instruction(tok, first, ntok, &symbols, ln, 1, &out);
        free(scratch);
    }

    symtab_free(&symbols);
    lines_free(&lines);

    *out_len = out.len;
    return out.data;
}
