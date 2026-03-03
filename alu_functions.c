#include "alu_functions.h"

void alu_not(CPU *cpu, Args *args) {
    *cpu->I = *cpu->A;
    *cpu->A = ~(*cpu->I);
    if (args->v > 1) printf("\tExecuted:\tNOT\n");
}

void alu_bsl(CPU *cpu, Args *args) {
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I << 1;
    if (args->v > 1) printf("\tExecuted:\tBSL\n");
}

void alu_bsr(CPU *cpu, Args *args) {
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I >> 1;
    if (args->v > 1) printf("\tExecuted:\tBSR\n");
}

void alu_brl(CPU *cpu, Args *args) {
    *cpu->I = *cpu->A;
    *cpu->A = brl8(*cpu->I, 1);
    if (args->v > 1) printf("\tExecuted:\tBRL\n");
}

void alu_brr(CPU *cpu, Args *args) {
    *cpu->I = *cpu->A;
    *cpu->A = brr8(*cpu->I, 1);
    if (args->v > 1) printf("\tExecuted:\tBRR\n");
}

void alu_psh(CPU *cpu, Args *args) {
    uint8_t SP8[2] = {*(cpu->SP[0]), *(cpu->SP[1])};
    uint16_t SP16;
    addr_convert_8_to_16(&SP16, SP8);
    SP16--;
    cpu->M[SP16] = *cpu->A;
    addr_convert_16_to_8(SP8, SP16);
    *(cpu->SP[0]) = SP8[0];
    *(cpu->SP[1]) = SP8[1];
    if (args->v > 1) printf("\tExecuted:\tPSH\n");
}

void alu_pop(CPU *cpu, Args *args) {
    uint8_t SP8[2] = {*(cpu->SP[0]), *(cpu->SP[1])};
    uint16_t SP16;
    addr_convert_8_to_16(&SP16, SP8);
    *cpu->A = cpu->M[SP16];
    cpu->M[SP16] = 0;
    SP16++;
    addr_convert_16_to_8(SP8, SP16);
    *(cpu->SP[0]) = SP8[0];
    *(cpu->SP[1]) = SP8[1];
    if (args->v > 1) printf("\tExecuted:\tPOP\n");
}

void alu_ret(CPU *cpu, Args *args) {
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
    if (args->v > 1) printf("\tExecuted:\tRET\n");
}

void alu_ldr(CPU *cpu, Args *args) {
    uint8_t reg_id = *cpu->IR[0] & 0b00001111;
    *cpu->A = cpu->R[reg_id];
    if (args->v > 1) printf("\tExecuted:\tLDR %d\n", reg_id);
}

void alu_str(CPU *cpu, Args *args) {
    uint8_t reg_id = *cpu->IR[0] & 0b00001111;
    cpu->R[reg_id] = *cpu->A;
    if (args->v > 1) printf("\tExecuted:\tSTR %d\n", reg_id);
}

void alu_orr(CPU *cpu, Args *args) {
    uint8_t reg_id = *cpu->IR[0] & 0b00001111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I | cpu->R[reg_id];
    if (args->v > 1) printf("\tExecuted:\tORR\n");
}

void alu_and(CPU *cpu, Args *args) {
    uint8_t reg_id = *cpu->IR[0] & 0b00001111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I & cpu->R[reg_id];
    if (args->v > 1) printf("\tExecuted:\tAND\n");
}

void alu_xor(CPU *cpu, Args *args) {
    uint8_t reg_id = *cpu->IR[0] & 0b00001111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I ^ cpu->R[reg_id];
    if (args->v > 1) printf("\tExecuted:\tXOR\n");
}

void alu_add(CPU *cpu, Args *args) {
    uint8_t reg_id = *cpu->IR[0] & 0b00001111;
    *cpu->I = *cpu->A;
    *cpu->A = *cpu->I + cpu->R[reg_id];
    cpu_set_flag(cpu, FLAG_POS_CARRY, (*cpu->A < *cpu->I));
    if (args->v > 1) printf("\tExecuted:\tADD\n");
}

void alu_ldi(CPU *cpu, Args *args) {
    uint8_t imm = *cpu->IR[1];
    *cpu->A = imm;
    if (args->v > 1) printf("\tExecuted:\tLDI %d\n", imm);
}

void alu_ldm(CPU *cpu, Args *args) {
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    *cpu->A = cpu->M[addr16];
    if (args->v > 1) printf("\tExecuted:\tLDM %d\n", addr16);
}

void alu_stm(CPU *cpu, Args *args) {
    uint16_t addr16;
    uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
    addr_convert_8_to_16(&addr16, addr8);
    cpu->M[addr16] = *cpu->A;
    if (args->v > 1) printf("\tExecuted:\tSTM %d\n", addr16);
}

void alu_jmp(CPU *cpu, Args *args) {
    *(cpu->PC[0]) = *(cpu->IR[1]);
    *(cpu->PC[1]) = *(cpu->IR[2]);
    if (args->v > 1) {
        uint16_t addr16;
        uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
        addr_convert_8_to_16(&addr16, addr8);
        printf("\tExecuted:\tJMP %d\n", addr16);
    }
}

void alu_jc0(CPU *cpu, Args *args) {
    if (!cpu_get_flag(cpu, FLAG_POS_CARRY)) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
    if (args->v > 1) {
        uint16_t addr16;
        uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
        addr_convert_8_to_16(&addr16, addr8);
        printf("\tExecuted:\tJC0 %d\n", addr16);
    }
}

void alu_jc1(CPU *cpu, Args *args) {
    if (cpu_get_flag(cpu, FLAG_POS_CARRY)) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
    if (args->v > 1) {
        uint16_t addr16;
        uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
        addr_convert_8_to_16(&addr16, addr8);
        printf("\tExecuted:\tJC1 %d\n", addr16);
    }
}

void alu_ja0(CPU *cpu, Args *args) {
    if (*cpu->A == 0) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
    if (args->v > 1) {
        uint16_t addr16;
        uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
        addr_convert_8_to_16(&addr16, addr8);
        printf("\tExecuted:\tJA0 %d\n", addr16);
    }
}

void alu_ja1(CPU *cpu, Args *args) {
    if (*cpu->A != 0) {
        *(cpu->PC[0]) = *(cpu->IR[1]);
        *(cpu->PC[1]) = *(cpu->IR[2]);
    }
    if (args->v > 1) {
        uint16_t addr16;
        uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
        addr_convert_8_to_16(&addr16, addr8);
        printf("\tExecuted:\tJA1 %d\n", addr16);
    }
}

void alu_cll(CPU *cpu, Args *args) {
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
    if (args->v > 1) {
        uint16_t addr16;
        uint8_t addr8[2] = {*(cpu->IR[1]), *(cpu->IR[2])};
        addr_convert_8_to_16(&addr16, addr8);
        printf("\tExecuted:\tCLL %d\n", addr16);
    }
}
