#include "alu_functions.h"

#include <stdint.h>
#include <stdio.h>

#include "cpu_functions.h"
#include "utility.h"

void alu_not(CPU *cpu, char *msg, size_t msg_size) {
    *cpu->I = *cpu->A;
    *cpu->A = ~(*cpu->I);
    snprintf(msg, msg_size, "NOT");
}

void alu_bsl(CPU *cpu, char *msg, size_t msg_size) {
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I << 1;
    snprintf(msg, msg_size, "BSL");
}

void alu_bsr(CPU *cpu, char *msg, size_t msg_size) {
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I >> 1;
    snprintf(msg, msg_size, "BSR");
}

void alu_brl(CPU *cpu, char *msg, size_t msg_size) {
    *cpu->I = *cpu->A;
    *cpu->A = brl8(*cpu->I, 1);
    snprintf(msg, msg_size, "BRL");
}

void alu_brr(CPU *cpu, char *msg, size_t msg_size) {
    *cpu->I = *cpu->A;
    *cpu->A = brr8(*cpu->I, 1);
    snprintf(msg, msg_size, "BRR");
}

void alu_psh(CPU *cpu, char *msg, size_t msg_size) {
    uint8_t SP8[2] = {*(cpu->SP[0]), *(cpu->SP[1])};
    uint16_t SP16;
    addr_convert_8_to_16(&SP16, SP8);
    SP16--;
    cpu->M[SP16] = *cpu->A;
    addr_convert_16_to_8(SP8, SP16);
    *(cpu->SP[0]) = SP8[0];
    *(cpu->SP[1]) = SP8[1];
    snprintf(msg, msg_size, "PSH");
}

void alu_pop(CPU *cpu, char *msg, size_t msg_size) {
    uint8_t SP8[2] = {*(cpu->SP[0]), *(cpu->SP[1])};
    uint16_t SP16;
    addr_convert_8_to_16(&SP16, SP8);
    *cpu->A = cpu->M[SP16];
    cpu->M[SP16] = 0;
    SP16++;
    addr_convert_16_to_8(SP8, SP16);
    *(cpu->SP[0]) = SP8[0];
    *(cpu->SP[1]) = SP8[1];
    snprintf(msg, msg_size, "POP");
}

void alu_ret(CPU *cpu, char *msg, size_t msg_size) {
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
    snprintf(msg, msg_size, "RET");
}

void alu_ldr(CPU *cpu, char *msg, size_t msg_size) {
    uint8_t reg_id = *cpu->IR[1] & 0b00011111;
    *cpu->A = cpu->R[reg_id];
    snprintf(msg, msg_size, "LDR %d", reg_id);
}

void alu_str(CPU *cpu, char *msg, size_t msg_size) {
    uint8_t reg_id = *cpu->IR[1] & 0b00011111;
    cpu->R[reg_id] = *(cpu->A);
    snprintf(msg, msg_size, "STR %d", reg_id);
}

void alu_orr(CPU *cpu, char *msg, size_t msg_size) {
    uint8_t reg_id = *cpu->IR[1] & 0b00011111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I | cpu->R[reg_id];
    snprintf(msg, msg_size, "ORR %d", reg_id);
}

void alu_and(CPU *cpu, char *msg, size_t msg_size) {
    uint8_t reg_id = *cpu->IR[1] & 0b00011111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I & cpu->R[reg_id];
    snprintf(msg, msg_size, "AND %d", reg_id);
}

void alu_xor(CPU *cpu, char *msg, size_t msg_size) {
    uint8_t reg_id = *cpu->IR[1] & 0b00011111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I ^ cpu->R[reg_id];
    snprintf(msg, msg_size, "XOR %d", reg_id);
}

void alu_add(CPU *cpu, char *msg, size_t msg_size) {
    uint8_t reg_id = *cpu->IR[1] & 0b00011111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I + cpu->R[reg_id];
    cpu_set_flag(cpu, FLAG_POS_CARRY, (*cpu->A < *cpu->I));
    snprintf(msg, msg_size, "ADD %d", reg_id);
}

void alu_ldi(CPU *cpu, char *msg, size_t msg_size) {
    uint8_t imm = *cpu->IR[1];
    *cpu->A = imm;
    snprintf(msg, msg_size, "LDI %d", imm);
}

void alu_ldm(CPU *cpu, char *msg, size_t msg_size) {
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    *cpu->A = cpu->M[addr16];
    snprintf(msg, msg_size, "LDM %d", addr16);
}

void alu_stm(CPU *cpu, char *msg, size_t msg_size) {
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    cpu->M[addr16] = *cpu->A;
    snprintf(msg, msg_size, "STM %d", addr16);
}

void alu_jmp(CPU *cpu, char *msg, size_t msg_size) {
    *(cpu->PC[0]) = *(cpu->IR[1]);
    *(cpu->PC[1]) = *(cpu->IR[2]);
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    snprintf(msg, msg_size, "JMP %d", addr16);
}

void alu_jc0(CPU *cpu, char *msg, size_t msg_size) {
    if (!cpu_get_flag(cpu, FLAG_POS_CARRY)) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    snprintf(msg, msg_size, "JC0 %d", addr16);
}

void alu_jc1(CPU *cpu, char *msg, size_t msg_size) {
    if (cpu_get_flag(cpu, FLAG_POS_CARRY)) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    snprintf(msg, msg_size, "JC1 %d", addr16);
}

void alu_ja0(CPU *cpu, char *msg, size_t msg_size) {
    if (*cpu->A == 0) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    snprintf(msg, msg_size, "JA0 %d", addr16);
}

void alu_ja1(CPU *cpu, char *msg, size_t msg_size) {
    if (*cpu->A != 0) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    snprintf(msg, msg_size, "JA1 %d", addr16);
}

void alu_cll(CPU *cpu, char *msg, size_t msg_size) {
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
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    snprintf(msg, msg_size, "CLL %d", addr16);
}
