#include "alu_functions.h"

#include <stdint.h>
#include <stdio.h>

#include "cpu_functions.h"
#include "utility.h"

char *alu_not(CPU *cpu) {
    *cpu->I = *cpu->A;
    *cpu->A = ~(*cpu->I);
    return "NOT";
}

char *alu_bsl(CPU *cpu) {
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I << 1;
    return "BSL";
}

char *alu_bsr(CPU *cpu) {
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I >> 1;
    return "BSR";
}

char *alu_brl(CPU *cpu) {
    *cpu->I = *cpu->A;
    *cpu->A = brl8(*cpu->I, 1);
    return "BRL";
}

char *alu_brr(CPU *cpu) {
    *cpu->I = *cpu->A;
    *cpu->A = brr8(*cpu->I, 1);
    return "BRR";
}

char *alu_psh(CPU *cpu) {
    uint8_t SP8[2] = {*(cpu->SP[0]), *(cpu->SP[1])};
    uint16_t SP16;
    addr_convert_8_to_16(&SP16, SP8);
    SP16--;
    cpu->M[SP16] = *cpu->A;
    addr_convert_16_to_8(SP8, SP16);
    *(cpu->SP[0]) = SP8[0];
    *(cpu->SP[1]) = SP8[1];
    return "PSH";
}

char *alu_pop(CPU *cpu) {
    uint8_t SP8[2] = {*(cpu->SP[0]), *(cpu->SP[1])};
    uint16_t SP16;
    addr_convert_8_to_16(&SP16, SP8);
    *cpu->A = cpu->M[SP16];
    cpu->M[SP16] = 0;
    SP16++;
    addr_convert_16_to_8(SP8, SP16);
    *(cpu->SP[0]) = SP8[0];
    *(cpu->SP[1]) = SP8[1];
    return "POP";
}

char *alu_ret(CPU *cpu) {
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
    return "RET";
}

char *alu_ldr(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[1] & 0b00011111;
    *cpu->A = cpu->R[reg_id];
    char *msg;
    asprintf(&msg, "LDR %d", reg_id);
    return msg;
}

char *alu_str(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[1] & 0b00011111;
    cpu->R[reg_id] = *(cpu->A);
    char *msg;
    asprintf(&msg, "STR %d", reg_id);
    return msg;
}

char *alu_orr(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[1] & 0b00011111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I | cpu->R[reg_id];
    char *msg;
    asprintf(&msg, "ORR %d", reg_id);
    return msg;
}

char *alu_and(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[1] & 0b00011111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I & cpu->R[reg_id];
    char *msg;
    asprintf(&msg, "AND %d", reg_id);
    return msg;
}

char *alu_xor(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[1] & 0b00011111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I ^ cpu->R[reg_id];
    char *msg;
    asprintf(&msg, "XOR %d", reg_id);
    return msg;
}

char *alu_add(CPU *cpu) {
    uint8_t reg_id = *cpu->IR[1] & 0b00011111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I + cpu->R[reg_id];
    cpu_set_flag(cpu, FLAG_POS_CARRY, (*cpu->A < *cpu->I));
    char *msg;
    asprintf(&msg, "ADD %d", reg_id);
    return msg;
}

char *alu_ldi(CPU *cpu) {
    uint8_t imm = *cpu->IR[1];
    *cpu->A = imm;
    char *msg;
    asprintf(&msg, "LDI %d", imm);
    return msg;
}

char *alu_ldm(CPU *cpu) {
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    *cpu->A = cpu->M[addr16];
    char *msg;
    asprintf(&msg, "LDM %d", addr16);
    return msg;
}

char *alu_stm(CPU *cpu) {
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    cpu->M[addr16] = *cpu->A;
    char *msg;
    asprintf(&msg, "STM %d", addr16);
    return msg;
}

char *alu_jmp(CPU *cpu) {
    *(cpu->PC[0]) = *(cpu->IR[1]);
    *(cpu->PC[1]) = *(cpu->IR[2]);
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    char *msg;
    asprintf(&msg, "JMP %d", addr16);
    return msg;
}

char *alu_jc0(CPU *cpu) {
    if (!cpu_get_flag(cpu, FLAG_POS_CARRY)) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    char *msg;
    asprintf(&msg, "JC0 %d", addr16);
    return msg;
}

char *alu_jc1(CPU *cpu) {
    if (cpu_get_flag(cpu, FLAG_POS_CARRY)) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    char *msg;
    asprintf(&msg, "JC1 %d", addr16);
    return msg;
}

char *alu_ja0(CPU *cpu) {
    if (*cpu->A == 0) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    char *msg;
    asprintf(&msg, "JA0 %d", addr16);
    return msg;
}

char *alu_ja1(CPU *cpu) {
    if (*cpu->A != 0) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    char *msg;
    asprintf(&msg, "JA1 %d", addr16);
    return msg;
}

char *alu_cll(CPU *cpu) {
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
    char *msg;
    asprintf(&msg, "CLL %d", addr16);
    return msg;
}
