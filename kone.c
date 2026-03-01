// #include <stdbool.h>

#include "cpu_struct.h"
#include "cpu_functions.h"

int main(int argc, char *argv[]) {
    Args args;
    parse_args(&args, argc, argv);

    CPU cpu;
    cpu_reset(&cpu);
    cpu_boot_file(&cpu, args.bootfile);

    uint16_t PC16;
    do {
        printf("%d\n", *cpu.PC[0]);
        addr_convert_8_to_16(&PC16, *cpu.PC);
        cpu_fetch(&cpu, &args);
        cpu_decode_exec(&cpu);
    } while (PC16 < MEM_SIZE);

    return 0;
}
