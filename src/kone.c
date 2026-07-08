#define _DARWIN_C_SOURCE
#define _BSD_SOURCE

#include <sys/mman.h>
#include <unistd.h>
#include <sys/wait.h>

#include "cpu_struct.h"
#include "cpu_functions.h"
#include "display_struct.h"
#include "display_functions.h"

int main(int argc, char *argv[]) {
    Args args;
    parse_args(&args, argc, argv);

    CPU *cpu = mmap(NULL, sizeof(CPU), PROT_READ | PROT_WRITE,
                    MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    cpu_init(cpu);
    cpu_reset(cpu);
    cpu_boot_file(cpu, args.bootfile);

    pid_t cpu_pid = fork();
    if (cpu_pid == 0) {
        cpu_init(cpu);
        uint16_t PC16 = 0;
        if (args.v > 0) cpu_print_count(cpu);
        if (args.v > 2) cpu_print_state(cpu);
        do {
            uint8_t PC8[2] = {*cpu->PC[0], *cpu->PC[1]};
            addr_convert_8_to_16(&PC16, PC8);
            cpu_fetch(cpu, &args);
            cpu_decode_exec(cpu, &args);
        } while (PC16 < MEM_SIZE);
        exit(0);
    }

    pid_t display_pid = fork();
    if (display_pid == 0) {
        signal(SIGINT, display_cleanup);
        cpu_init(cpu);
        Display display;
        display_reset(&display);
        printf(
            "\033[?25l\033[?1049h"); // hide cursor, switch to alternate screen
        while (1) {
            display_fetch(cpu, &display);
            display_print(&display);
            usleep(100);
        }
        printf("\033[?25h\033[?1049l"); // show cursor, switch to main screen
        exit(0);
    }

    waitpid(display_pid, NULL, 0);
    waitpid(cpu_pid, NULL, 0);
    return 0;
}
