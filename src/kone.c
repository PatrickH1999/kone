#define _DARWIN_C_SOURCE
#define _DEFAULT_SOURCE

#define OUT_FRAMERATE 20
#define KBRD_RATE 20

// display_fetch must be polled well above the CPU's register write rate, or
// display.kasm-style programs (which write a new char every loop iteration
// with no consume handshake) get overwritten before the display reads them.
// The terminal is only redrawn at OUT_FRAMERATE; polling is decoupled and
// much faster.
#define DISP_POLL_RATE 2000

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>

#include "args.h"
#include "cpu_functions.h"
#include "cpu_struct.h"
#include "display_functions.h"
#include "display_struct.h"
#include "keyboard_functions.h"
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
            for (int i = 0; i < DISP_POLL_RATE / OUT_FRAMERATE; i++) {
                display_fetch(cpu, display);
                sleep_ns(1000000000L / DISP_POLL_RATE);
            }
            if (!args.log) print_out(cpu, cpu_msg, display, &args);
        }
        exit(0);
    }

    pid_t keyboard_pid = fork();
    if (keyboard_pid == 0) {
        keyboard_init();
        signal(SIGINT, keyboard_cleanup);
        while (1) {
            keyboard_push_cpu(cpu);
            usleep(1e6 / KBRD_RATE);
        }
        exit(0);
    }

    waitpid(display_pid, NULL, 0);
    waitpid(cpu_pid, NULL, 0);
    return 0;
}
