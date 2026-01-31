#include "cpu_functions.h"

void cpu_reset(CPU *cpu) {
    cpu->B = 0;
    cpu->A = 0;
    cpu->I = 0;
    memset(cpu->R, 0, sizeof(cpu->R));
    memset(cpu->M, 0, sizeof(cpu->M));
    cpu->PC = 0;
    cpu->C = false;
    cpu->IR0 = 0;
    cpu->IR1 = 0;
}

void cpu_fetch(CPU *cpu) {
    cpu->IR0 = cpu->M[cpu->PC];
    if ((cpu->IR0 & 0b10000000) == 0b10000000) {
        cpu->PC++;
        cpu->IR1 = cpu->M[cpu->PC];
    }
    cpu->PC++;
}
