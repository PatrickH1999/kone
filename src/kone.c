#define _DARWIN_C_SOURCE
#define _DEFAULT_SOURCE

#define OUT_FRAMERATE 20

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#include "args.h"
#include "cpu_functions.h"
#include "cpu_struct.h"
#include "display_functions.h"
#include "display_struct.h"
#include "utility.h"

int main(int argc, char *argv[]) {
    Args args;
    parse_args(&args, argc, argv);

    CPU *cpu = mmap(NULL, sizeof(CPU), PROT_READ | PROT_WRITE,
                    MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    char *cpu_msg = mmap(NULL, CPU_MSG_SIZE, PROT_READ | PROT_WRITE,
                         MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    cpu_init(cpu);
    cpu_reset(cpu);
    if (cpu_boot_file(cpu, args.bootfile) != 0) {
        fprintf(stderr, "Error: could not open boot file: %s\n", args.bootfile);
        exit(EXIT_FAILURE);
    }

    Display *display = mmap(NULL, sizeof(CPU), PROT_READ | PROT_WRITE,
                            MAP_SHARED | MAP_ANONYMOUS, -1, 0);

    pid_t cpu_pid = fork();
    if (cpu_pid == 0) {
        cpu_init(cpu);
        uint16_t PC16 = 0;
        do {
            uint8_t PC8[2] = {*cpu->PC[0], *cpu->PC[1]};
            addr_convert_8_to_16(&PC16, PC8);
            cpu_fetch(cpu, &args);
            cpu_decode_exec(cpu, cpu_msg, CPU_MSG_SIZE, &args);
            if (args.log) print_out(cpu, cpu_msg, display, &args);
        } while (PC16 < MEM_SIZE);
        exit(0);
    }

    pid_t display_pid = fork();
    if (display_pid == 0) {
        cpu_init(cpu);
        display_reset(display);
        if (!args.log) {
            signal(SIGINT, out_cleanup);
            printf("\033[?25l\033[?1049h"); // hide cursor, switch to alternate
                                            // screen
        }
        while (1) {
            struct timespec t1, t2;
            clock_gettime(CLOCK_MONOTONIC, &t1);
            double elapsed = 0.0;
            do {
                display_fetch(cpu, display);
                clock_gettime(CLOCK_MONOTONIC, &t2);
                elapsed =
                    (t2.tv_sec - t1.tv_sec) + (t2.tv_nsec - t1.tv_nsec) / 1e9;
            } while (elapsed < (1.0 / OUT_FRAMERATE));
            if (!args.log) print_out(cpu, cpu_msg, display, &args);
        }
        exit(0);
    }

    waitpid(display_pid, NULL, 0);
    waitpid(cpu_pid, NULL, 0);
    return 0;
}
