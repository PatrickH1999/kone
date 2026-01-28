#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    uint8_t B;   // bus
    uint8_t A;   // accumulator
    uint8_t I;   // input buffer
    uint8_t R[8];   // register
    uint8_t M[2048];   // memory
    uint16_t PC;   // program counter
    bool C;   // carry
    uint8_t IR;   // instruction register
} CPU;

void cpu_reset(CPU *cpu) {
    cpu->B = 0;
    cpu->A = 0;
    cpu->I = 0;
    memset(cpu->R, 0, sizeof(cpu->R));
    memset(cpu->M, 0, sizeof(cpu->M));
    cpu->PC = 0;
    cpu->C = false;
    cpu->IR = 0;
}

void cpu_fetch(CPU *cpu) {
    cpu->IR = cpu->M[cpu->PC];
}

int main() {
    CPU cpu;
    cpu_reset(&cpu);
    cpu.M[0] = 0xA0;
    cpu_fetch(&cpu);
    printf("%u\n", cpu.IR);
}
