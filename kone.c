// #include <stdbool.h>

#include "cpu_struct.h"
#include "cpu_functions.h"

int main(int argc, char *argv[]) {
    Args args;
    parse_args(&args, argc, argv);

    CPU cpu;
    cpu_reset(&cpu);
    cpu_boot_file(&cpu, args.bootfile);

    uint16_t PC16 = 0;
    if (args.v > 0) printf("[%d]\n", PC16);
    if (args.v > 2) cpu_print_state(&cpu);
    do {
        addr_convert_8_to_16(&PC16, *cpu.PC);
        cpu_fetch(&cpu, &args);
        cpu_decode_exec(&cpu, &args);
        printf("DISPLAY: %d, %d, %d, %d, %d", cpu.D[0], cpu.D[1], cpu.D[2], cpu.D[3], cpu.D[4]);
    } while (PC16 < MEM_SIZE);

    return 0;
}
