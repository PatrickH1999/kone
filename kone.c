#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define NOP 0b00000000
#define LDR 0b00001000
#define STR 0b00010000

typedef struct {
    uint8_t B;   // bus
    uint8_t A;   // accumulator
    uint8_t I;   // input buffer
    uint8_t R[8];   // register
    uint8_t M[2048];   // memory
    uint16_t PC;   // program counter
    bool C;   // carry
    uint8_t IR0;   // instruction register (cycle 0)
    uint8_t IR1;   // instruction register (cycle 1)
} CPU;

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
    cpu->IR1 = cpu->M[cpu->PC + 1];
}

void cpu_ldr(CPU *cpu) {
    uint8_t reg_id = cpu->IR0 & 0b00000111;
    cpu->A = cpu->R[reg_id];
}

void cpu_str(CPU *cpu) {
    uint8_t reg_id = cpu->IR0 & 0b00000111;
    cpu->R[reg_id] = cpu->A;
}

void cpu_exec(CPU *cpu) {
    uint8_t opcode = cpu->IR0 & 0b11111000;
    switch (opcode) {
        case NOP: break;
        case LDR: cpu_ldr(cpu); break;
        case STR: cpu_str(cpu); break;
    }
}

int main() {
    CPU cpu;
    cpu_reset(&cpu);
    cpu.R[2] = 184;
    cpu.M[0] = 0b00001010;
    cpu_fetch(&cpu);
    cpu_exec(&cpu);
    printf("%u\n", cpu.A);
}
