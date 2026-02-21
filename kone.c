// #include <stdbool.h>

#include "cpu_struct.h"
#include "cpu_functions.h"

int main(int argc, char *argv[]) {
    if (argc != 2) return print_usage(argv);

    CPU cpu;
    cpu_reset(&cpu);
    const char *bootfile = argv[1];
    cpu_boot_file(&cpu, bootfile);

    uint16_t PC16;
    do {
        addr_convert_8_to_16(&PC16, *cpu.PC);
        cpu_fetch(&cpu);
        cpu_decode_exec(&cpu);
    } while (PC16 < MEM_SIZE);

    return 0;
}
