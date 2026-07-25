#include "cpu_functions.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

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

    const uint16_t SP16 = MEM_SIZE - (DISP_NCOLS * DISP_NROWS) - 1;
    uint8_t SP8[2];
    addr_convert_16_to_8(SP8, SP16);
    *(cpu->SP[0]) = SP8[0];
    *(cpu->SP[1]) = SP8[1];

    const uint16_t PC16 = 0;
    uint8_t PC8[2];
    addr_convert_16_to_8(PC8, PC16);
    *(cpu->PC[0]) = PC8[0];
    *(cpu->PC[1]) = PC8[1];
}

int cpu_boot_file(CPU *cpu, const char *path) {
    FILE *const f = fopen(path, "rb");
    if (!f) return -1;

    const size_t n = fread(cpu->M, 1, MEM_SIZE, f);
    fclose(f);

    for (size_t i = n; i < MEM_SIZE; ++i)
        cpu->M[i] = 0;

    return 0;
}

void cpu_pc_increment(CPU *cpu, const Args *args) {
    if (args->cycle_sleep != 0) sleep_ns((long)args->cycle_sleep * 1000000L);

    uint16_t PC16;
    addr_convert_8_to_16(&PC16, *cpu->PC);

    cpu->cycle++;
    if (PC16 < (MEM_SIZE - 1))
        PC16++;
    else
        PC16 = 0;

    addr_convert_16_to_8(*cpu->PC, PC16);
}

void cpu_fetch(CPU *cpu, const Args *args) {
    uint16_t PC16;

    addr_convert_8_to_16(&PC16, *cpu->PC);
    *cpu->IR[0] = cpu->M[PC16];
    cpu_pc_increment(cpu, args);

    const uint8_t opcode = cpu->M[PC16];
    const int opcode_flag_pos = get_pos_first_1_in_byte(opcode);

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

void cpu_decode_exec(CPU *cpu, char *msg, const size_t msg_size,
                     const Args *args) {
    (void)args;
    uint8_t opcode = *cpu->IR[0];
    const int opcode_flag_pos = get_pos_first_1_in_byte(opcode);
    if (opcode_flag_pos == OC_FLAG_POS_R) opcode = opcode & 0b11110000;

    msg[0] = '\0';
    switch (opcode) {
    case NOP:
        break;
    case NOT:
        alu_not(cpu, msg, msg_size);
        break;
    case BSL:
        alu_bsl(cpu, msg, msg_size);
        break;
    case BSR:
        alu_bsr(cpu, msg, msg_size);
        break;
    case BRL:
        alu_brl(cpu, msg, msg_size);
        break;
    case BRR:
        alu_brr(cpu, msg, msg_size);
        break;
    case RET:
        alu_ret(cpu, msg, msg_size);
        break;
    case LDR:
        alu_ldr(cpu, msg, msg_size);
        break;
    case STR:
        alu_str(cpu, msg, msg_size);
        break;
    case PSH:
        alu_psh(cpu, msg, msg_size);
        break;
    case POP:
        alu_pop(cpu, msg, msg_size);
        break;
    case ORR:
        alu_orr(cpu, msg, msg_size);
        break;
    case AND:
        alu_and(cpu, msg, msg_size);
        break;
    case XOR:
        alu_xor(cpu, msg, msg_size);
        break;
    case ADD:
        alu_add(cpu, msg, msg_size);
        break;
    case LDI:
        alu_ldi(cpu, msg, msg_size);
        break;
    case LDM:
        alu_ldm(cpu, msg, msg_size);
        break;
    case STM:
        alu_stm(cpu, msg, msg_size);
        break;
    case JMP:
        alu_jmp(cpu, msg, msg_size);
        break;
    case JC0:
        alu_jc0(cpu, msg, msg_size);
        break;
    case JC1:
        alu_jc1(cpu, msg, msg_size);
        break;
    case JA0:
        alu_ja0(cpu, msg, msg_size);
        break;
    case JA1:
        alu_ja1(cpu, msg, msg_size);
        break;
    case CLL:
        alu_cll(cpu, msg, msg_size);
        break;
    default:
        fprintf(stderr, "Error: invalid opcode %u\n", opcode);
        exit(EXIT_FAILURE);
        break;
    }
}

uint8_t cpu_get_flag(const CPU *cpu, const uint8_t flag_pos) {
    assert(flag_pos < (8 * sizeof(uint8_t)));
    const uint8_t value = (*cpu->F >> flag_pos) & 0b00000001;
    return value;
}

void cpu_set_flag(const CPU *cpu, const uint8_t flag_pos, const uint8_t value) {
    assert(value == 0 || value == 1);
    assert(flag_pos < (8 * sizeof(uint8_t)));
    const uint8_t mask = value << flag_pos;
    *cpu->F &= ~(1 << flag_pos);
    *cpu->F |= mask;
}

void cpu_print_count(const CPU *cpu) {
    const uint8_t PC8[2] = {*(cpu->PC[0]), *(cpu->PC[1])};
    uint16_t PC16;
    addr_convert_8_to_16(&PC16, PC8);
    printf("\n\n[ %d : %d ]\n", cpu->cycle, PC16);
}

void cpu_print_state(const CPU *cpu) {
    const int n = 22; // number of general purpose registers
    const int regs_per_row = 3;
    for (int reg_id = 0; reg_id < n; reg_id++) {
        const int mod = reg_id % regs_per_row;
        const char *prefix, *suffix;
        if (mod == 0) {
            prefix = "\t\t";
            suffix = (reg_id < (n - 1)) ? "" : "\n";
        } else if (0 < mod && mod < (regs_per_row - 1)) {
            prefix = "\t";
            suffix = (reg_id < (n - 1)) ? "" : "\n";
        } else if (mod == (regs_per_row - 1)) {
            prefix = "\t";
            suffix = "\n";
        }
        printf("%sR%2d: %3d%s", prefix, reg_id, cpu->R[reg_id], suffix);
    }
    const uint8_t SP8[2] = {*(cpu->SP[0]), *(cpu->SP[1])};
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
    const uint8_t PC8[2] = {*(cpu->PC[0]), *(cpu->PC[1])};
    uint16_t PC16;
    addr_convert_8_to_16(&PC16, PC8);
    printf("\t\tR30-31 (program counter): %d\n", PC16);
}
