#include <stdbool.h>

#include "cpu_struct.h"
#include "cpu_functions.h"

int main(int argc, char *argv[]) {
    if (argc != 2) return print_usage(argv);

    CPU cpu;
    cpu_reset(&cpu);
    const char *bootfile = argv[1];
    cpu_boot_file(&cpu, bootfile);
    while (cpu.PC < MEM_SIZE) {
        printf("R6: %u, R7: %u\n", cpu.R[6], cpu.R[7]);
        cpu_fetch(&cpu);
        cpu_decode_exec(&cpu);
    }

    return 0;
}
