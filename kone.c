#include <stdio.h>

#include "cpu_struct.h"
#include "cpu_functions.h"

#define NOP 0b00000000
#define NOT 0b00001000

#define LDR 0b00010000
#define STR 0b00011000
#define LDM 0b10010000
#define STM 0b10011000
#define LDI 0b10001000

#define ORR 0b00100000
#define AND 0b00101000
#define XOR 0b00110000
#define ADD 0b00111000

#define BSL 0b01000000
#define BSR 0b01001000
#define BRL 0b01010000
#define BRR 0b01011000

#define JMP 0b10100000
#define JC0 0b10101000
#define JC1 0b10110000
#define JA0 0b11101000
#define JA1 0b11110000

uint8_t brl8(uint8_t x, unsigned n)
{
    n &= 7;  // n mod 8
    return (x << n) | (x >> (8 - n));
}

uint8_t brr8(uint8_t x, unsigned n)
{
    n &= 7;  // n mod 8
    return (x >> n) | (x << (8 - n));
}

void alu_ldr(CPU *cpu) {
    uint8_t reg_id = cpu->IR0 & 0b00000111;
    cpu->A = cpu->R[reg_id];
}

void alu_str(CPU *cpu) {
    uint8_t reg_id = cpu->IR0 & 0b00000111;
    cpu->R[reg_id] = cpu->A;
}

void alu_ldm(CPU *cpu) {
    uint16_t addr = (0b00000111 & cpu->IR0) << 8;
    addr += cpu->IR1;
    cpu->A = cpu->M[addr];
}

void alu_stm(CPU *cpu) {
    uint16_t addr = (0b00000111 & cpu->IR0) << 8;
    addr += cpu->IR1;
    cpu->M[addr] = cpu->A;
}

void alu_ldi(CPU *cpu) {
    uint8_t imm = cpu->IR1;
    cpu->A = imm;
}

void alu_orr(CPU *cpu) {
    uint8_t reg_id = cpu->IR0 & 0b00000111;
    cpu->I = cpu->A;
    cpu->A = cpu->I | cpu->R[reg_id];
}

void alu_and(CPU *cpu) {
    uint8_t reg_id = cpu->IR0 & 0b00000111;
    cpu->I = cpu->A;
    cpu->A = cpu->I & cpu->R[reg_id];
}

void alu_xor(CPU *cpu) {
    uint8_t reg_id = cpu->IR0 & 0b00000111;
    cpu->I = cpu->A;
    cpu->A = cpu->I ^ cpu->R[reg_id];
}

void alu_not(CPU *cpu) {
    cpu->I = cpu->A;
    cpu->A = ~cpu->I;
}

void alu_add(CPU *cpu) {
    uint8_t reg_id = cpu->IR0 & 0b00000111;
    cpu->I = cpu->A;
    cpu->A = cpu->I + cpu->R[reg_id];
    cpu->C = (cpu->A < cpu->I);
}

void alu_bsl(CPU *cpu) {
    cpu->I = cpu->A;
    cpu->A = cpu->I << 1;
}

void alu_bsr(CPU *cpu) {
    cpu->I = cpu->A;
    cpu->A = cpu->I >> 1;
}

void alu_brl(CPU *cpu) {
    cpu->I = cpu->A;
    cpu->A = brl8(cpu->I, 1);
}

void alu_brr(CPU *cpu) {
    cpu->I = cpu->A;
    cpu->A = brr8(cpu->I, 1);
}

void alu_jmp(CPU *cpu) {
    uint16_t addr = (0b00000111 & cpu->IR0) << 8;
    addr += cpu->IR1;
    cpu->PC = addr;
}

void alu_jc0(CPU *cpu) {
    if (!cpu->C) {
        uint16_t addr = (0b00000111 & cpu->IR0) << 8;
        addr += cpu->IR1;
        cpu->PC = addr;
    }
}

void alu_jc1(CPU *cpu) {
    if (cpu->C) {
        uint16_t addr = (0b00000111 & cpu->IR0) << 8;
        addr += cpu->IR1;
        cpu->PC = addr;
    }
}

void alu_ja0(CPU *cpu) {
    if (cpu->A == 0) {
        uint16_t addr = (0b00000111 & cpu->IR0) << 8;
        addr += cpu->IR1;
        cpu->PC = addr;
    }
}

void alu_ja1(CPU *cpu) {
    if (cpu->A != 0) {
        uint16_t addr = (0b00000111 & cpu->IR0) << 8;
        addr += cpu->IR1;
        cpu->PC = addr;
    }
}

void cpu_decode_exec(CPU *cpu) {
    uint8_t opcode = cpu->IR0 & 0b11111000;
    switch (opcode) {
        case NOP: break;
        case NOT: alu_not(cpu); break;
        case LDR: alu_ldr(cpu); break;
        case STR: alu_str(cpu); break;
        case LDM: alu_ldm(cpu); break;
        case STM: alu_stm(cpu); break;
        case LDI: alu_ldi(cpu); break;
        case ORR: alu_orr(cpu); break;
        case AND: alu_and(cpu); break;
        case XOR: alu_xor(cpu); break;
        case ADD: alu_add(cpu); break;
        case BSL: alu_bsl(cpu); break;
        case BSR: alu_bsr(cpu); break;
        case BRL: alu_brl(cpu); break;
        case BRR: alu_brr(cpu); break;
        case JMP: alu_jmp(cpu); break;
        case JC0: alu_jc0(cpu); break;
        case JC1: alu_jc1(cpu); break;
        case JA0: alu_ja0(cpu); break;
        case JA1: alu_ja1(cpu); break;
    }
}

int main() {
    CPU cpu;
    cpu_reset(&cpu);
    cpu.M[0] = 0b10001000;   // load imm "1" into acc
    cpu.M[1] = 0b00000001;   // """
    cpu.M[2] = 0b00011001;   // store acc to reg1
    cpu.M[3] = 0b10001000;   // load imm "0" into acc
    cpu.M[4] = 0b00000000;   // """
    cpu.M[5] = 0b00111001;   // LOOP: add reg1 to acc
    cpu.M[6] = 0b00011000;   // store acc to reg0
    cpu.M[7] = 0b10100000;   // jump to LOOP
    cpu.M[8] = 0b00000101;   // """

    while (true) {
        cpu_fetch(&cpu);
        cpu_decode_exec(&cpu);
        printf("%u\n", cpu.R[0]);
    }

    return 0;
}
