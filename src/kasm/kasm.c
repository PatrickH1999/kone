#include "assembler.h"

#include <getopt.h>
#include <libgen.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

typedef struct {
    const char *input;  // input assembly file (.kasm)
    const char *output; // output binary file (.bin)
} Args;

static struct option long_options[] = {{"input", required_argument, NULL, 'i'},
                                       {"output", required_argument, NULL, 'o'},
                                       {"help", no_argument, NULL, 'h'},
                                       {NULL, 0, NULL, 0}};

static void print_usage(char *argv[]) {
    fprintf(stderr, "Usage: %s -i INPUT -o OUTPUT [-h]\n", basename(argv[0]));
    exit(EXIT_FAILURE);
}

static void print_help(char *argv[]) {
    fprintf(stdout, "Usage: %s -i INPUT -o OUTPUT [OPTIONS]\n\n",
            basename(argv[0]));

    fprintf(stdout, "Options:\n");
    fprintf(stdout,
            "  -i, --input  FILE    Input assembly source file (required)\n");
    fprintf(stdout, "  -o, --output FILE    Output binary file (required)\n");
    fprintf(stdout, "  -h, --help           Show this help and exit\n\n");

    fprintf(stdout, "Examples:\n");
    fprintf(stdout, "  %s -i examples/patrick.kasm -o bin/patrick.bin\n",
            basename(argv[0]));

    exit(EXIT_SUCCESS);
}

static void parse_args(Args *args, int argc, char *argv[]) {
    args->input = NULL;
    args->output = NULL;

    int opt;
    while ((opt = getopt_long(argc, argv, "i:o:h", long_options, NULL)) != -1) {
        switch (opt) {
        case 'i':
            args->input = optarg;
            break;
        case 'o':
            args->output = optarg;
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
