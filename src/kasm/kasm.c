#include "assembler.h"

#include <libgen.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

typedef struct {
    const char *input;  // input assembly file (.kasm)
    const char *output; // output binary file (.bin)
} Args;

static void print_usage(char *argv[]) {
    fprintf(stderr, "Usage: %s -i INPUT.kasm -o OUTPUT.bin\n",
            basename(argv[0]));
    exit(EXIT_FAILURE);
}

static void parse_args(Args *args, int argc, char *argv[]) {
    args->input = NULL;
    args->output = NULL;

    int opt;
    while ((opt = getopt(argc, argv, "i:o:")) != -1) {
        switch (opt) {
        case 'i':
            args->input = optarg;
            break;
        case 'o':
            args->output = optarg;
            break;
        default:
            print_usage(argv);
        }
    }
    if (!args->input || !args->output) print_usage(argv);
}

int main(int argc, char *argv[]) {
    Args args;
    parse_args(&args, argc, argv);

    size_t len;
    uint8_t *code = assemble_file(args.input, &len);

    FILE *out = fopen(args.output, "wb");
    if (!out) {
        fprintf(stderr, "kasm: error: cannot open '%s' for writing\n",
                args.output);
        free(code);
        return EXIT_FAILURE;
    }
    if (len > 0 && fwrite(code, 1, len, out) != len) {
        fprintf(stderr, "kasm: error: failed to write '%s'\n", args.output);
        fclose(out);
        free(code);
        return EXIT_FAILURE;
    }

    fclose(out);
    free(code);
    return EXIT_SUCCESS;
}
