#ifndef ARGS_H
#define ARGS_H

#include <libgen.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

typedef struct {
    const char *bootfile;     // bootfile
    unsigned int cycle_sleep; // sleep time between clock cycles [ms]
    int v;                    // verbosity
} Args;

void parse_args(Args *args, int argc, char *argv[]);
void print_usage(char *argv[]);

#endif
