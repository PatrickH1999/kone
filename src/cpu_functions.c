#include "cpu_functions.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include "alu_functions.h"
#include "utility.h"

void cpu_init(CPU *cpu) {
    // Stack pointer (SP):
    cpu->SP[0] = &cpu->R[22];
    cpu->SP[1] = &cpu->R[23];

    // input register (I), accumulator (A), Flags (F)
    cpu->I = &cpu->R[24];
    cpu->A = &cpu->R[25];
    cpu->F = &cpu->R[26];

    // Instruction register (IC):
    cpu->IR[0] = &cpu->R[27];
    cpu->IR[1] = &cpu->R[28];
    cpu->IR[2] = &cpu->R[29];

    // Program counter (PC):
    cpu->PC[0] = &cpu->R[30];
    cpu->PC[1] = &cpu->R[31];
}

void cpu_reset(CPU *cpu) {
    cpu->cycle = 0;

    memset(cpu->R, 0, sizeof(cpu->R));
    memset(cpu->M, 0, sizeof(cpu->M));

    uint16_t SP16 = MEM_SIZE - (DISP_NCOLS * DISP_NROWS) - 1;
    uint8_t SP8[2];
    addr_convert_16_to_8(SP8, SP16);
    *(cpu->SP[0]) = SP8[0];
    *(cpu->SP[1]) = SP8[1];

    uint16_t PC16 = 0;
    uint8_t PC8[2];
    addr_convert_16_to_8(PC8, PC16);
    *(cpu->PC[0]) = PC8[0];
    *(cpu->PC[1]) = PC8[1];
}

int cpu_boot_file(CPU *cpu, const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) return -1;

    size_t n = fread(cpu->M, 1, MEM_SIZE, f);
    fclose(f);

    for (size_t i = n; i < MEM_SIZE; ++i)
        cpu->M[i] = 0;

    return 0;
}

void cpu_pc_increment(CPU *cpu, Args *args) {
    const struct timespec ts = {.tv_sec = 0,
                                .tv_nsec = args->cycle_sleep * 1000000};
    nanosleep(&ts, NULL);

    uint16_t PC16;
    addr_convert_8_to_16(&PC16, *cpu->PC);

    cpu->cycle++;
    if (PC16 < (MEM_SIZE - 1))
        PC16++;
    else
        PC16 = 0;

    addr_convert_16_to_8(*cpu->PC, PC16);
}

void cpu_fetch(CPU *cpu, Args *args) {
    uint16_t PC16;

    addr_convert_8_to_16(&PC16, *cpu->PC);
    *cpu->IR[0] = cpu->M[PC16];
    cpu_pc_increment(cpu, args);

    uint8_t opcode = cpu->M[PC16];
    int opcode_flag_pos = get_pos_first_1_in_byte(opcode);

    if (opcode_flag_pos == OC_FLAG_POS_R || opcode_flag_pos == OC_FLAG_POS_I ||
        opcode_flag_pos == OC_FLAG_POS_M || opcode_flag_pos == OC_FLAG_POS_V) {
        addr_convert_8_to_16(&PC16, *cpu->PC);
        *cpu->IR[1] = cpu->M[PC16];
        cpu_pc_increment(cpu, args);
    }
    if (opcode_flag_pos == OC_FLAG_POS_M) {
        addr_convert_8_to_16(&PC16, *cpu->PC);
        *cpu->IR[2] = cpu->M[PC16];
        cpu_pc_increment(cpu, args);
    }
}

void cpu_decode_exec(CPU *cpu, Args *args) {
    uint8_t opcode = *cpu->IR[0];
    int opcode_flag_pos = get_pos_first_1_in_byte(opcode);
    if (opcode_flag_pos == OC_FLAG_POS_R) opcode = opcode & 0b11110000;

    char *msg;
    switch (opcode) {
    case NOP:
        break;
    case NOT:
        msg = alu_not(cpu);
        break;
    case BSL:
        msg = alu_bsl(cpu);
        break;
    case BSR:
        msg = alu_bsr(cpu);
        break;
    case BRL:
        msg = alu_brl(cpu);
        break;
    case BRR:
        msg = alu_brr(cpu);
        break;
    case RET:
        msg = alu_ret(cpu);
        break;
    case LDR:
        msg = alu_ldr(cpu);
        break;
    case STR:
        msg = alu_str(cpu);
        break;
    case PSH:
        msg = alu_psh(cpu);
        break;
    case POP:
        msg = alu_pop(cpu);
        break;
    case ORR:
        msg = alu_orr(cpu);
        break;
    case AND:
        msg = alu_and(cpu);
        break;
    case XOR:
        msg = alu_xor(cpu);
        break;
    case ADD:
        msg = alu_add(cpu);
        break;
    case LDI:
        msg = alu_ldi(cpu);
        break;
    case LDM:
        msg = alu_ldm(cpu);
        break;
    case STM:
        msg = alu_stm(cpu);
        break;
    case JMP:
        msg = alu_jmp(cpu);
        break;
    case JC0:
        msg = alu_jc0(cpu);
        break;
    case JC1:
        msg = alu_jc1(cpu);
        break;
    case JA0:
        msg = alu_ja0(cpu);
        break;
    case JA1:
        msg = alu_ja1(cpu);
        break;
    case CLL:
        msg = alu_cll(cpu);
        break;
    }
    if (args->v > 1) printf("\t%s\n", msg);
}

uint8_t cpu_get_flag(CPU *cpu, uint8_t flag_pos) {
    assert(flag_pos < (8 * sizeof(uint8_t)));
    uint8_t value = (*cpu->F >> flag_pos) & 0b00000001;
    return value;
}

void cpu_set_flag(CPU *cpu, uint8_t flag_pos, uint8_t value) {
    assert(value == 0 || value == 1);
    assert(flag_pos < (8 * sizeof(uint8_t)));
    uint8_t mask = value << flag_pos;
    *cpu->F &= ~(1 << flag_pos);
    *cpu->F |= mask;
}

void cpu_print_count(CPU *cpu) {
    uint8_t PC8[2] = {*(cpu->PC[0]), *(cpu->PC[1])};
    uint16_t PC16;
    addr_convert_8_to_16(&PC16, PC8);
    printf("\n\n[ %d : %d ]\n", cpu->cycle, PC16);
}

void cpu_print_state(CPU *cpu) {
    int n = 22; // number of general purpose registers
    int regs_per_row = 3;
    for (int reg_id = 0; reg_id < n; reg_id++) {
        int mod = reg_id % regs_per_row;
        const char *prefix, *suffix;
        if (mod == 0) {
            prefix = "\t\t";
            suffix = "";
        } else if (0 < mod && mod < (regs_per_row - 1)) {
            prefix = "\t";
            suffix = "";
        } else if (mod == (regs_per_row - 1)) {
            prefix = "\t";
            suffix = "\n";
        }
        printf("%sR%2d: %3d%s", prefix, reg_id, cpu->R[reg_id], suffix);
    }
    uint8_t SP8[2] = {*(cpu->SP[0]), *(cpu->SP[1])};
    uint16_t SP16;
    addr_convert_8_to_16(&SP16, SP8);
    printf("\t\tR22-R23 (stack pointer): %d\n", SP16);
    printf("\t\tR24 (input left): %d\n", *(cpu->I));
    printf("\t\tR25 (accumulator): %d\n", *(cpu->A));
    printf("\t\tR26 (flags): ");
    print_bin(*(cpu->F));
    printf("\n");
    printf("\t\tR27-R29 (instruction register): %d %d %d\n", *(cpu->IR[0]),
           *(cpu->IR[1]), *(cpu->IR[2]));
    uint8_t PC8[2] = {*(cpu->PC[0]), *(cpu->PC[1])};
    uint16_t PC16;
    addr_convert_8_to_16(&PC16, PC8);
    printf("\t\tR30-31 (program counter): %d\n", PC16);
}
