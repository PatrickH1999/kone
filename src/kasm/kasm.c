#include "assembler.h"

#include <getopt.h>
#include <libgen.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

typedef struct {
    const char *input;  // input assembly file (.kasm)
    const char *output; // output binary file (.bin)
    SymTab constants;   // -D NAME=VALUE
} Args;

static struct option long_options[] = {{"input", required_argument, NULL, 'i'},
                                       {"output", required_argument, NULL, 'o'},
                                       {"define", required_argument, NULL, 'D'},
                                       {"help", no_argument, NULL, 'h'},
                                       {NULL, 0, NULL, 0}};

static void print_usage(char *argv[]) {
    fprintf(stderr, "Usage: %s -i INPUT -o OUTPUT [-D NAME=VALUE]... [-h]\n",
            basename(argv[0]));
    exit(EXIT_FAILURE);
}

static void print_help(char *argv[]) {
    fprintf(stdout, "Usage: %s -i INPUT -o OUTPUT [OPTIONS]\n\n",
            basename(argv[0]));

    fprintf(stdout, "Options:\n");
    fprintf(stdout,
            "  -i, --input  FILE    Input assembly source file (required)\n");
    fprintf(stdout, "  -o, --output FILE    Output binary file (required)\n");
    fprintf(
        stdout,
        "  -D, --define NAME=VALUE\n"
        "                       Constant usable as an operand; repeatable\n");
    fprintf(stdout, "  -h, --help           Show this help and exit\n\n");

    fprintf(stdout, "Examples:\n");
    fprintf(stdout,
            "  %s -D DISP_NCOLS=20 -D DISP_NROWS=4 -i examples/hello.kasm "
            "-o bin/hello.bin\n",
            basename(argv[0]));

    exit(EXIT_SUCCESS);
}

static void parse_args(Args *args, int argc, char *argv[]) {
    args->input = NULL;
    args->output = NULL;
    symtab_init(&args->constants);

    int opt;
    while ((opt = getopt_long(argc, argv, "i:o:D:h", long_options, NULL)) !=
           -1) {
        switch (opt) {
        case 'i':
            args->input = optarg;
            break;
        case 'o':
            args->output = optarg;
            break;
        case 'D':
            if (!assembler_define(&args->constants, optarg)) {
                fprintf(stderr,
                        "kasm: error: bad -D '%s' (NAME=VALUE, NAME not a "
                        "number and given once, VALUE at most 0xFFFF)\n",
                        optarg);
                exit(EXIT_FAILURE);
            }
            break;
        case 'h':
            print_help(argv);
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
    uint8_t *code = assemble_file(args.input, &args.constants, &len);
    symtab_free(&args.constants);

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
