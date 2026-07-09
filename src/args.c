#include "args.h"

void print_usage(char *argv[]) {
    fprintf(stderr, "Usage: %s -b BOOTFILE [-v[v[v]]] [-t MSEC]\n",
            basename(argv[0]));
    exit(EXIT_FAILURE);
}

void parse_args(Args *args, int argc, char *argv[]) {
    args->bootfile = NULL;
    args->cycle_sleep = 1; // [ms]
    args->v = 0;
    int opt;
    int found = 0;
    while ((opt = getopt(argc, argv, "b:t:v")) != -1) {
        switch (opt) {
        case 'b':
            args->bootfile = optarg;
            found++;
            break;
        case 't':
            args->cycle_sleep = strtoul(optarg, NULL, 10);
            break;
        case 'v':
            args->v++;
            break;
        default:
            print_usage(argv);
        }
    }
    if (found < 1) print_usage(argv);
}
