#include <stdbool.h>

#include "cpu_struct.h"
#include "cpu_functions.h"

int main(int argc, char *argv[]) {
    if (argc != 2) return print_usage(argv);

    const char *bootfile = argv[1];
    CPU cpu;
    cpu_reset(&cpu);
    cpu_boot_file(&cpu, bootfile);
    while (true) {
        cpu_fetch(&cpu);
        cpu_decode_exec(&cpu);
    }

    return 0;
}
