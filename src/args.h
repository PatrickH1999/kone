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
    int log;                  // If =1: logs are written continuously at every
                              // clock cycle
} Args;

void parse_args(Args *args, int argc, char *argv[]);
void print_usage(char *argv[]);

#endif
