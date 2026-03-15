#include "cpu_functions.h"

void cpu_reset(CPU *cpu) {
    memset(cpu->R, 0, sizeof(cpu->R));
    memset(cpu->M, 0, sizeof(cpu->M));

    cpu->PC[0] = &cpu->R[14];
    cpu->PC[1] = &cpu->R[15];
    cpu->IR[0] = &cpu->R[11];
    cpu->IR[1] = &cpu->R[12];
    cpu->IR[2] = &cpu->R[13];

    cpu->F = &cpu->R[10];
    cpu->A = &cpu->R[9];
    cpu->I = &cpu->R[8];

    cpu->SP[0] = &cpu->R[6];
    cpu->SP[1] = &cpu->R[7];
    // set stack pointer (SP) to (MEM_SIZE - 1):
    uint16_t SP16 = MEM_SIZE - 1;
    uint8_t SP8[2];
    addr_convert_16_to_8(SP8, SP16);
    *(cpu->SP[0]) = SP8[0];
    *(cpu->SP[1]) = SP8[1];

    cpu->DP[0] = &cpu->R[4];
    cpu->DP[1] = &cpu->R[5];
    // set display pointer (DP) to 0:
    *(cpu->DP[0]) = 0;
    *(cpu->DP[1]) = 0;
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
    const struct timespec ts = {.tv_sec = 0, .tv_nsec = args->cycle_sleep * 1000000};
    nanosleep(&ts, NULL);

    uint16_t PC16;
    addr_convert_8_to_16(&PC16, *cpu->PC);

    if (PC16 < (MEM_SIZE - 1))
        PC16++;
    else
        PC16 = 0;

    addr_convert_16_to_8(*cpu->PC, PC16);

    if (args->v > 0) printf("\n\n[%d]\n", PC16);
    if (args->v > 2) cpu_print_state(cpu);
}

void cpu_fetch(CPU *cpu, Args *args) {
    uint16_t PC16;

    addr_convert_8_to_16(&PC16, *cpu->PC);
    *cpu->IR[0] = cpu->M[PC16];
    cpu_pc_increment(cpu, args);

    uint8_t opcode = cpu->M[PC16];
    int opcode_flag_pos = get_pos_first_1_in_byte(opcode);

    if (opcode_flag_pos == OC_FLAG_POS_I || opcode_flag_pos == OC_FLAG_POS_M ||
        opcode_flag_pos == OC_FLAG_POS_V) {
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

    switch (opcode) {
    case NOP:
        break;
    case NOT:
        alu_not(cpu, args);
        break;
    case BSL:
        alu_bsl(cpu, args);
        break;
    case BSR:
        alu_bsr(cpu, args);
        break;
    case BRL:
        alu_brl(cpu, args);
        break;
    case BRR:
        alu_brr(cpu, args);
        break;
    case RET:
        alu_ret(cpu, args);
        break;
    case LDR:
        alu_ldr(cpu, args);
        break;
    case STR:
        alu_str(cpu, args);
        break;
    case PSH:
        alu_psh(cpu, args);
        break;
    case POP:
        alu_pop(cpu, args);
        break;
    case ORR:
        alu_orr(cpu, args);
        break;
    case AND:
        alu_and(cpu, args);
        break;
    case XOR:
        alu_xor(cpu, args);
        break;
    case ADD:
        alu_add(cpu, args);
        break;
    case LDI:
        alu_ldi(cpu, args);
        break;
    case LDM:
        alu_ldm(cpu, args);
        break;
    case STM:
        alu_stm(cpu, args);
        break;
    case JMP:
        alu_jmp(cpu, args);
        break;
    case JC0:
        alu_jc0(cpu, args);
        break;
    case JC1:
        alu_jc1(cpu, args);
        break;
    case JA0:
        alu_ja0(cpu, args);
        break;
    case JA1:
        alu_ja1(cpu, args);
        break;
    case CLL:
        alu_cll(cpu, args);
        break;
    }
}

uint8_t cpu_get_flag(CPU *cpu, uint8_t flag_pos) {
    assert(flag_pos < (8 * sizeof(uint8_t)));
    uint8_t value = (*cpu->F >> flag_pos) & 0b00000001;
    return value;
}

void cpu_set_flag(CPU *cpu, uint8_t flag_pos, uint8_t value) {
    assert(value == 0 || value == 1);
    assert(flag_pos < (8 * sizeof(uint8_t)));
    uint8_t new_entry = value << flag_pos;
    *cpu->F = *cpu->F | new_entry;
}

void cpu_print_state(CPU *cpu) {
    printf("\t\tR0: %d\n", cpu->R[0]);
    printf("\t\tR1: %d\n", cpu->R[1]);
    printf("\t\tR2: %d\n", cpu->R[2]);
    printf("\t\tR3: %d\n", cpu->R[3]);
    printf("\t\tR4: %d\n", cpu->R[4]);
    printf("\t\tR5: %d\n\n", cpu->R[5]);
    uint8_t SP8[2] = {*(cpu->SP[0]), *(cpu->SP[1])};
    uint16_t SP16;
    addr_convert_8_to_16(&SP16, SP8);
    printf("\t\tR6-R7 (stack pointer): %d\n", SP16);
    printf("\t\tR8 (input left): %d\n", *(cpu->I));
    printf("\t\tR9 (accumulator): %d\n", *(cpu->A));
    printf("\t\tR10 (flags): ");
    print_bin(*(cpu->F));
    printf("\n");
    printf("\t\tR11-R13 (instruction register): %d %d %d\n", *(cpu->IR[0]), *(cpu->IR[1]),
           *(cpu->IR[2]));
    uint8_t PC8[2] = {*(cpu->PC[0]), *(cpu->PC[1])};
    uint16_t PC16;
    addr_convert_8_to_16(&PC16, PC8);
    printf("\t\tR14-15 (program counter): %d\n", PC16);
}
