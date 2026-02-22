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

void cpu_pc_increment(CPU *cpu) {
    const struct timespec ts = {.tv_sec = 0, .tv_nsec = CYCLE_SLEEP * 1000000};
    nanosleep(&ts, NULL);

    uint16_t PC16;
    addr_convert_8_to_16(&PC16, *cpu->PC);

    if (PC16 < (MEM_SIZE - 1))
        PC16++;
    else
        PC16 = 0;

    addr_convert_16_to_8(*cpu->PC, PC16);
}

void cpu_fetch(CPU *cpu) {
    uint16_t PC16;

    addr_convert_8_to_16(&PC16, *cpu->PC);
    *cpu->IR[0] = cpu->M[PC16];
    cpu_pc_increment(cpu);

    uint8_t opcode = cpu->M[PC16];
    int opcode_flag_pos = get_pos_first_1_in_byte(opcode);

    if (opcode_flag_pos == OC_FLAG_POS_I || opcode_flag_pos == OC_FLAG_POS_M ||
        opcode_flag_pos == OC_FLAG_POS_V) {
        addr_convert_8_to_16(&PC16, *cpu->PC);
        *cpu->IR[1] = cpu->M[PC16];
        cpu_pc_increment(cpu);
    }
    if (opcode_flag_pos == OC_FLAG_POS_M) {
        addr_convert_8_to_16(&PC16, *cpu->PC);
        *cpu->IR[2] = cpu->M[PC16];
        cpu_pc_increment(cpu);
    }
}

void cpu_decode_exec(CPU *cpu) {
    uint8_t opcode = *cpu->IR[0];
    int opcode_flag_pos = get_pos_first_1_in_byte(opcode);
    if (opcode_flag_pos == OC_FLAG_POS_R) opcode = opcode & 0b11110000;

    switch (opcode) {
    case NOP:
        break;
    case NOT:
        alu_not(cpu);
        break;
    case BSL:
        alu_bsl(cpu);
        break;
    case BSR:
        alu_bsr(cpu);
        break;
    case BRL:
        alu_brl(cpu);
        break;
    case BRR:
        alu_brr(cpu);
        break;
    case RET:
        alu_ret(cpu);
        break;
    case LDR:
        alu_ldr(cpu);
        break;
    case STR:
        alu_str(cpu);
        break;
    case PSH:
        alu_psh(cpu);
        break;
    case POP:
        alu_pop(cpu);
        break;
    case ORR:
        alu_orr(cpu);
        break;
    case AND:
        alu_and(cpu);
        break;
    case XOR:
        alu_xor(cpu);
        break;
    case ADD:
        alu_add(cpu);
        break;
    case LDI:
        alu_ldi(cpu);
        break;
    case LDM:
        alu_ldm(cpu);
        break;
    case STM:
        alu_stm(cpu);
        break;
    case JMP:
        alu_jmp(cpu);
        break;
    case JC0:
        alu_jc0(cpu);
        break;
    case JC1:
        alu_jc1(cpu);
        break;
    case JA0:
        alu_ja0(cpu);
        break;
    case JA1:
        alu_ja1(cpu);
        break;
    case CLL:
        alu_cll(cpu);
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
