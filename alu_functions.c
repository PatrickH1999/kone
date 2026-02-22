#include "alu_functions.h"

void alu_not(CPU *cpu) {
    *cpu->I = *cpu->A;
    *cpu->A = ~(*cpu->I);
}

void alu_bsl(CPU *cpu) {
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I << 1;
}

void alu_bsr(CPU *cpu) {
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I >> 1;
}

void alu_brl(CPU *cpu) {
    *cpu->I = *cpu->A;
    *cpu->A = brl8(*cpu->I, 1);
}

void alu_brr(CPU *cpu) {
    *cpu->I = *cpu->A;
    *cpu->A = brr8(*cpu->I, 1);
}

// TO BE IMPLEMENTED
void alu_ret(CPU *cpu) {
    cpu = cpu;
}

void alu_ldr(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[0] & 0b00001111;
    *cpu->A = cpu->R[reg_id];
}

void alu_str(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[0] & 0b00001111;
    cpu->R[reg_id] = *cpu->A;
}

// TO BE IMPLEMENTED
void alu_psh(CPU *cpu) {
    cpu = cpu;
}

// TO BE IMPLEMENTED
void alu_pop(CPU *cpu) {
    cpu = cpu;  
}

void alu_orr(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[0] & 0b00001111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I | cpu->R[reg_id];
}

void alu_and(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[0] & 0b00001111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I & cpu->R[reg_id];
}

void alu_xor(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[0] & 0b00001111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I ^ cpu->R[reg_id];
}

void alu_add(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[0] & 0b00001111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I + cpu->R[reg_id];
    alu_set_flag(cpu, FLAG_POS_CARRY, (*cpu->A < *cpu->I));
}

void alu_ldi(CPU *cpu) {
    uint8_t imm = *cpu->IR[1];
    *cpu->A = imm;
}

void alu_ldm(CPU *cpu) {
    uint16_t addr = (0b00000111 & *cpu->IR[0]) << 8 * sizeof(uint8_t);
    addr += *cpu->IR[1];
    *cpu->A = cpu->M[addr];
}

void alu_stm(CPU *cpu) {
    uint16_t addr = (0b00000111 & *cpu->IR[0]) << 8 * sizeof(uint8_t);
    addr += *cpu->IR[1];
    cpu->M[addr] = *cpu->A;
}

void alu_jmp(CPU *cpu) {
    uint16_t addr = (0b00000111 & *cpu->IR[0]) << 8 * sizeof(uint8_t);
    addr += *cpu->IR[1];
    *cpu->PC[0] = addr;
}

void alu_jc0(CPU *cpu) {
    if (!alu_get_flag(cpu, FLAG_POS_CARRY)) {
        uint16_t addr = (0b00000111 & *cpu->IR[0]) << 8 * sizeof(uint8_t);
        addr += *cpu->IR[1];
        *cpu->PC[0] = addr;
    }
}

void alu_jc1(CPU *cpu) {
    if (alu_get_flag(cpu, FLAG_POS_CARRY)) {
        uint16_t addr = (0b00000111 & *cpu->IR[0]) << 8 * sizeof(uint8_t);
        addr += *cpu->IR[1];
        *cpu->PC[0] = addr;
    }
}

void alu_ja0(CPU *cpu) {
    if (*cpu->A == 0) {
        uint16_t addr = (0b00000111 & *cpu->IR[0]) << 8 * sizeof(uint8_t);
        addr += *cpu->IR[1];
        *cpu->PC[0] = addr;
    }
}

void alu_ja1(CPU *cpu) {
    if (*cpu->A != 0) {
        uint16_t addr = (0b00000111 & *cpu->IR[0]) << 8 * sizeof(uint8_t);
        addr += *cpu->IR[1];
        *cpu->PC[0] = addr;
    }
}

// TO BE IMPLEMENTED
void alu_cll(CPU *cpu) {
    cpu = cpu;
}

void alu_out(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[0] & 0b00000111;
    printf("Output: %u\n", cpu->R[reg_id]);
}

void alu_inn(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[0] & 0b00000111;
    int ok = 0;
    while (!ok) {
        printf("Input (0...255): ");
        ok = scanf_uint8(&cpu->R[reg_id]);
        if (!ok) printf("Error: Format.\n");
    }
}

uint8_t alu_get_flag(CPU *cpu, uint8_t flag_pos) {
    assert(flag_pos < (8 * sizeof(uint8_t)));
    uint8_t value = (*cpu->F >> flag_pos) & 0b00000001;
    return value;
}

void alu_set_flag(CPU *cpu, uint8_t flag_pos, uint8_t value) {
    assert(value == 0 || value == 1);
    assert(flag_pos < (8 * sizeof(uint8_t)));
    uint8_t new_entry = value << flag_pos;
    *cpu->F = *cpu->F | new_entry;
}
