#ifndef ARGS_H
#define ARGS_H

#include <getopt.h>
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

// Parses command line arguments into args, using getopt_long. Exits via
// print_usage on missing/invalid arguments, or via print_help if -h/--help
// is passed.
void parse_args(Args *args, int argc, char *argv[]);

// Prints a short one-line usage hint to stderr and exits with failure
// status. Called when required arguments are missing or an unknown option
// is passed.
void print_usage(char *argv[]);

// Prints a detailed help page listing every option, its short and long
// form, default value, and a description of its effect, then exits with
// success status.
void print_help(char *argv[]);

#endif
