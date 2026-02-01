#include "cpu_functions.h"

int cpu_boot_file(CPU *cpu, const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) return -1;

    size_t n = fread(cpu->M, 1, 2048, f);
    fclose(f);

    for (size_t i = n; i < 2048; ++i) cpu->M[i] = 0;
    
    return 0;
}

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

void cpu_pc_increment(CPU *cpu) { 
    const struct timespec ts = {
        .tv_sec = 0,
        .tv_nsec = CYCLE_SLEEP * 1000000   // 0.01s
    };
    nanosleep(&ts, NULL);
    cpu->PC++;
}

void cpu_fetch(CPU *cpu) {
    cpu->IR0 = cpu->M[cpu->PC];
    if ((cpu->IR0 & 0b10000000) == 0b10000000) {
        cpu->PC++;
        cpu->IR1 = cpu->M[cpu->PC];
    }
    cpu->PC++;
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
        case OUT: alu_out(cpu); break;
        case INN: alu_inn(cpu); break;
    }
}
