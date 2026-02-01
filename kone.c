#define _POSIX_C_SOURCE 199309L
#include <time.h>
#include <stdbool.h>

#include "cpu_struct.h"
#include "cpu_functions.h"

int main(int argc, char *argv[]) {
    if (argc != 2) return print_usage(argv);
    
    struct timespec ts = {
        .tv_sec = 0,
        .tv_nsec = 10000000   // 0.01s
    };

    const char *bootfile = argv[1];
    CPU cpu;
    cpu_reset(&cpu);
    cpu_boot_file(&cpu, bootfile);
    while (true) {
        cpu_fetch(&cpu);
        cpu_decode_exec(&cpu);
        nanosleep(&ts, NULL);
    }

    return 0;
}
