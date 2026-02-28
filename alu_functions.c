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

void alu_ret(CPU *cpu) {
    uint8_t SP8[2] = {*(cpu->SP[0]), *(cpu->SP[1])};
    uint16_t SP16;
    addr_convert_8_to_16(&SP16, SP8);
    *(cpu->PC[1]) = cpu->M[SP16];
    cpu->M[SP16] = 0;
    SP16++;
    *(cpu->PC[0]) = cpu->M[SP16];
    cpu->M[SP16] = 0;
    SP16++;
    addr_convert_16_to_8(SP8, SP16);
    *(cpu->SP[0]) = SP8[0];
    *(cpu->SP[1]) = SP8[1];
}

void alu_ldr(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[0] & 0b00001111;
    *cpu->A = cpu->R[reg_id];
}

void alu_str(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[0] & 0b00001111;
    cpu->R[reg_id] = *cpu->A;
}

void alu_psh(CPU *cpu) {
    uint8_t SP8[2] = {*(cpu->SP[0]), *(cpu->SP[1])};
    uint16_t SP16;
    addr_convert_8_to_16(&SP16, SP8);
    SP16--;
    cpu->M[SP16] = *cpu->A;
    addr_convert_16_to_8(SP8, SP16);
    *(cpu->SP[0]) = SP8[0];
    *(cpu->SP[1]) = SP8[1];
}

void alu_pop(CPU *cpu) {
    uint8_t SP8[2] = {*(cpu->SP[0]), *(cpu->SP[1])};
    uint16_t SP16;
    addr_convert_8_to_16(&SP16, SP8);
    *cpu->A = cpu->M[SP16];
    cpu->M[SP16] = 0;
    SP16++;
    addr_convert_16_to_8(SP8, SP16);
    *(cpu->SP[0]) = SP8[0];
    *(cpu->SP[1]) = SP8[1];
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
    cpu_set_flag(cpu, FLAG_POS_CARRY, (*cpu->A < *cpu->I));
}

void alu_ldi(CPU *cpu) {
    uint8_t imm = *cpu->IR[1];
    *cpu->A = imm;
}

void alu_ldm(CPU *cpu) {
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    *cpu->A = cpu->M[addr16];
}

void alu_stm(CPU *cpu) {
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    cpu->M[addr16] = *cpu->A;
}

void alu_jmp(CPU *cpu) {
    *(cpu->PC[0]) = *(cpu->IR[1]);
    *(cpu->PC[1]) = *(cpu->IR[2]);
}

void alu_jc0(CPU *cpu) {
    if (!cpu_get_flag(cpu, FLAG_POS_CARRY)) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
}

void alu_jc1(CPU *cpu) {
    if (cpu_get_flag(cpu, FLAG_POS_CARRY)) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
}

void alu_ja0(CPU *cpu) {
    if (*cpu->A == 0) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
}

void alu_ja1(CPU *cpu) {
    if (*cpu->A != 0) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
}

void alu_cll(CPU *cpu) {
    uint8_t SP8[2] = {*(cpu->SP[0]), *(cpu->SP[1])};
    uint16_t SP16;
    addr_convert_8_to_16(&SP16, SP8);
    SP16--;
    cpu->M[SP16] = *cpu->PC[0];
    SP16--;
    cpu->M[SP16] = *cpu->PC[1];
    addr_convert_16_to_8(SP8, SP16);
    *(cpu->SP[0]) = SP8[0];
    *(cpu->SP[1]) = SP8[1];
    *(cpu->PC[0]) = *(cpu->IR[1]);
    *(cpu->PC[1]) = *(cpu->IR[2]);
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
