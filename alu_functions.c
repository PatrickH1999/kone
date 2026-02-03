#include "alu_functions.h"

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

void alu_out(CPU *cpu) {
    uint8_t reg_id = cpu->IR0 & 0b00000111;
    printf("Output: %u\n", cpu->R[reg_id]);
}

void alu_inn(CPU *cpu) {
    uint8_t reg_id = cpu->IR0 & 0b00000111;
    int ok = 0;
    while (!ok) {
        printf("Input (0...255): ");
        ok = scanf_uint8(&cpu->R[reg_id]);
        if (!ok) printf("Error: Format.\n");
    }
}
