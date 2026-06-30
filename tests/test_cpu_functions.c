#include "test_cpu_functions.h"

int main() {
    CPU cpu;

    printf("\n\tTesting cpu_functions\n");
    test_cpu_init(&cpu);
    test_cpu_reset(&cpu);
    test_cpu_get_flag(&cpu);
    test_cpu_set_flag(&cpu);
    printf("\tALL PASS: cpu_functions\n");
    return 0;
}

void test_cpu_init(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    // pointers should point into R at correct indices
    assert(*cpu->SP[0] == cpu->R[22]);
    assert(*cpu->SP[1] == cpu->R[23]);
    assert(*cpu->I == cpu->R[24]);
    assert(*cpu->A == cpu->R[25]);
    assert(*cpu->F == cpu->R[26]);
    assert(*cpu->IR[0] == cpu->R[27]);
    assert(*cpu->IR[1] == cpu->R[28]);
    assert(*cpu->IR[2] == cpu->R[29]);
    assert(*cpu->PC[0] == cpu->R[30]);
    assert(*cpu->PC[1] == cpu->R[31]);
    printf("\t\tPASS: cpu_init\n");
}

void test_cpu_reset(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    // cycle should be 0
    assert(cpu->cycle == 0);
    // PC should be 0
    uint16_t PC16;
    uint8_t PC8[2] = {*cpu->PC[0], *cpu->PC[1]};
    addr_convert_8_to_16(&PC16, PC8);
    assert(PC16 == 0);
    // SP should be MEM_SIZE - DISP_NCOLS*DISP_NROWS - 1
    uint16_t SP16;
    uint8_t SP8[2] = {*cpu->SP[0], *cpu->SP[1]};
    addr_convert_8_to_16(&SP16, SP8);
    assert(SP16 == MEM_SIZE - (DISP_NCOLS * DISP_NROWS) - 1);
    // R and M should be zeroed (except SP/PC set above)
    for (int i = 0; i < 22; i++)
        assert(cpu->R[i] == 0);
    printf("\t\tPASS: cpu_reset\n");
}

void test_cpu_get_flag(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->F = 0b00000000;
    assert(cpu_get_flag(cpu, 0) == 0);
    assert(cpu_get_flag(cpu, 7) == 0);
    *cpu->F = 0b00000001;
    assert(cpu_get_flag(cpu, 0) == 1);
    assert(cpu_get_flag(cpu, 1) == 0);
    *cpu->F = 0b10000000;
    assert(cpu_get_flag(cpu, 7) == 1);
    assert(cpu_get_flag(cpu, 0) == 0);
    *cpu->F = 0b11111111;
    for (int i = 0; i < 8; i++)
        assert(cpu_get_flag(cpu, i) == 1);
    printf("\t\tPASS: cpu_get_flag\n");
}

void test_cpu_set_flag(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->F = 0x00;
    cpu_set_flag(cpu, 0, 1);
    assert(*cpu->F == 0b00000001);
    cpu_set_flag(cpu, 7, 1);
    assert(*cpu->F == 0b10000001);
    cpu_set_flag(cpu, 0, 0);
    assert(*cpu->F == 0b10000000);
    cpu_set_flag(cpu, 7, 0);
    assert(*cpu->F == 0b00000000);
    // set all bits one by one
    for (int i = 0; i < 8; i++)
        cpu_set_flag(cpu, i, 1);
    assert(*cpu->F == 0xFF);
    // clear all bits one by one
    for (int i = 0; i < 8; i++)
        cpu_set_flag(cpu, i, 0);
    assert(*cpu->F == 0x00);
    printf("\t\tPASS: cpu_set_flag\n");
}
