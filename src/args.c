#include "args.h"

static struct option long_options[] = {
    {"bootfile", required_argument, NULL, 'b'},
    {"clockspeed", required_argument, NULL, 't'},
    {"verbose", optional_argument, NULL, 'v'},
    {"log", no_argument, NULL, 'l'},
    {"help", no_argument, NULL, 'h'},
    {NULL, 0, NULL, 0}};

void print_usage(char *argv[]) {
    fprintf(stderr, "Usage: %s -b BOOTFILE [-v[v[v]]] [-t USEC] [-l] [-h]\n",
            basename(argv[0]));
    exit(EXIT_FAILURE);
}

void print_help(char *argv[]) {
    printf("Usage: %s -b BOOTFILE [-v[v[v]]] [-t USEC] [-l] [-h]\n\n",
           basename(argv[0]));

    printf("-b, --bootfile BOOTFILE\n");
    printf("    Default: (none, required)\n");
    printf("    Path to the binary boot file that is loaded into memory\n");
    printf("    before execution starts. This argument is required.\n\n");

    printf("-t, --clockspeed USEC\n");
    printf("    Default: 0 (run as fast as possible)\n");
    printf("    Number of microseconds to sleep between clock cycles.\n");
    printf("    Lower values run the simulation faster.\n\n");

    printf("-v, --verbose [0-3]\n");
    printf("    Default: 0\n");
    printf("    Sets the verbosity level of the output. Can be stacked\n");
    printf("    (e.g. -vvv) to increase the verbosity level by one per\n");
    printf("    occurrence, used bare (-v or --verbose) to increase it by\n");
    printf("    one, or given an explicit level (-v2 or --verbose=2) to\n");
    printf("    set it directly.\n\n");

    printf("-l, --log\n");
    printf("    Default: disabled\n");
    printf("    Enables continuous logging mode, where state is written to\n");
    printf("    the log at every clock cycle, instead of the interactive\n");
    printf("    display.\n\n");

    printf("-h, --help\n");
    printf("    Default: disabled\n");
    printf("    Prints this help page and exits.\n");

    exit(EXIT_SUCCESS);
}

void parse_args(Args *args, const int argc, char *argv[]) {
    args->bootfile = NULL;
    args->cycle_sleep = 0; // [us]; 0 = run as fast as possible
    args->v = 0;
    args->log = 0;
    int opt;
    int found = 0;
    while ((opt = getopt_long(argc, argv, "b:t:v::lh", long_options, NULL)) !=
           -1) {
        switch (opt) {
        case 'b':
            args->bootfile = optarg;
            found++;
            break;
        case 'l':
            args->log = 1;
            break;
        case 't':
            args->cycle_sleep = strtoul(optarg, NULL, 10);
            break;
        case 'v':
            if (optarg != NULL) {
                char *endptr;
                unsigned long level = strtoul(optarg, &endptr, 10);
                if (*endptr == '\0') {
                    // explicit level attached directly, e.g. --verbose=2 or
                    // -v2
                    args->v = (int)level;
                } else {
                    // stacked short flags folded into optarg by getopt_long,
                    // e.g. -vvv is parsed as opt='v' with optarg="vv"
                    args->v++;
                    for (const char *p = optarg; *p != '\0'; p++) {
                        if (*p == 'v') args->v++;
                    }
                }
            } else if (optind < argc && argv[optind][0] != '-') {
                // getopt_long only attaches optional arguments directly
                // (-v2, --verbose=2); check for a space-separated level too
                // (-v 2, --verbose 2) by peeking at the next argument.
                char *endptr;
                unsigned long level = strtoul(argv[optind], &endptr, 10);
                if (*endptr == '\0' && argv[optind][0] != '\0') {
                    args->v = (int)level;
                    optind++;
                } else {
                    args->v++;
                }
            } else {
                args->v++;
            }
            break;
        case 'h':
            print_help(argv);
            break;
        default:
            print_usage(argv);
        }
    }
    if (args->v > 3) args->v = 3;
    if (found < 1) print_usage(argv);
}
