#include "test_alu_functions.h"

int main() {
    CPU cpu;

    TEST_MODULE_BEGIN("alu_functions", 17);
    RUN_TEST(test_alu_not, &cpu);
    RUN_TEST(test_alu_bsl, &cpu);
    RUN_TEST(test_alu_bsr, &cpu);
    RUN_TEST(test_alu_brl, &cpu);
    RUN_TEST(test_alu_brr, &cpu);
    RUN_TEST(test_alu_ldi, &cpu);
    RUN_TEST(test_alu_ldr_str, &cpu);
    RUN_TEST(test_alu_orr, &cpu);
    RUN_TEST(test_alu_and, &cpu);
    RUN_TEST(test_alu_xor, &cpu);
    RUN_TEST(test_alu_add, &cpu);
    RUN_TEST(test_alu_ldm_stm, &cpu);
    RUN_TEST(test_alu_psh_pop, &cpu);
    RUN_TEST(test_alu_jmp, &cpu);
    RUN_TEST(test_alu_jc0_jc1, &cpu);
    RUN_TEST(test_alu_ja0_ja1, &cpu);
    RUN_TEST(test_alu_cll_ret, &cpu);
    TEST_MODULE_END("alu_functions", 17);
    return TEST_EXIT_CODE;
}

void test_alu_not(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->A = 0b10101010;
    alu_not(cpu, msg, sizeof(msg));
    assert(*cpu->A == 0b01010101);
    *cpu->A = 0x00;
    alu_not(cpu, msg, sizeof(msg));
    assert(*cpu->A == 0xFF);
}

void test_alu_bsl(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->A = 0b00000001;
    alu_bsl(cpu, msg, sizeof(msg));
    assert(*cpu->A == 0b00000010);
    *cpu->A = 0b10000000;
    alu_bsl(cpu, msg, sizeof(msg));
    assert(*cpu->A == 0b00000000);
}

void test_alu_bsr(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->A = 0b00000010;
    alu_bsr(cpu, msg, sizeof(msg));
    assert(*cpu->A == 0b00000001);
    *cpu->A = 0b00000001;
    alu_bsr(cpu, msg, sizeof(msg));
    assert(*cpu->A == 0b00000000);
}

void test_alu_brl(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->A = 0b10000000;
    alu_brl(cpu, msg, sizeof(msg));
    assert(*cpu->A == 0b00000001);
    *cpu->A = 0b00000001;
    alu_brl(cpu, msg, sizeof(msg));
    assert(*cpu->A == 0b00000010);
}

void test_alu_brr(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->A = 0b00000001;
    alu_brr(cpu, msg, sizeof(msg));
    assert(*cpu->A == 0b10000000);
    *cpu->A = 0b00000010;
    alu_brr(cpu, msg, sizeof(msg));
    assert(*cpu->A == 0b00000001);
}

void test_alu_ldi(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->IR[1] = 42;
    alu_ldi(cpu, msg, sizeof(msg));
    assert(*cpu->A == 42);
    *cpu->IR[1] = 0xFF;
    alu_ldi(cpu, msg, sizeof(msg));
    assert(*cpu->A == 0xFF);
}

void test_alu_ldr_str(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->A = 99;
    *cpu->IR[1] = 0;
    alu_str(cpu, msg, sizeof(msg));
    assert(cpu->R[0] == 99);
    *cpu->A = 0;
    alu_ldr(cpu, msg, sizeof(msg));
    assert(*cpu->A == 99);
}

void test_alu_orr(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->A = 0b10100000;
    cpu->R[0] = 0b00001010;
    *cpu->IR[1] = 0;
    alu_orr(cpu, msg, sizeof(msg));
    assert(*cpu->A == 0b10101010);
}

void test_alu_and(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->A = 0b11110000;
    cpu->R[0] = 0b10101010;
    *cpu->IR[1] = 0;
    alu_and(cpu, msg, sizeof(msg));
    assert(*cpu->A == 0b10100000);
}

void test_alu_xor(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->A = 0b11110000;
    cpu->R[0] = 0b10101010;
    *cpu->IR[1] = 0;
    alu_xor(cpu, msg, sizeof(msg));
    assert(*cpu->A == 0b01011010);
}

void test_alu_add(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->A = 10;
    cpu->R[0] = 5;
    *cpu->IR[1] = 0;
    alu_add(cpu, msg, sizeof(msg));
    assert(*cpu->A == 15);
    assert(!cpu_get_flag(cpu, FLAG_POS_CARRY));
    *cpu->A = 0xFF;
    cpu->R[0] = 1;
    alu_add(cpu, msg, sizeof(msg));
    assert(*cpu->A == 0x00);
    assert(cpu_get_flag(cpu, FLAG_POS_CARRY));
}

void test_alu_ldm_stm(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->A = 77;
    *cpu->IR[1] = 0x00;
    *cpu->IR[2] = 0x10;
    alu_stm(cpu, msg, sizeof(msg));
    *cpu->A = 0;
    alu_ldm(cpu, msg, sizeof(msg));
    assert(*cpu->A == 77);
}

void test_alu_psh_pop(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->A = 42;
    alu_psh(cpu, msg, sizeof(msg));
    *cpu->A = 0;
    alu_pop(cpu, msg, sizeof(msg));
    assert(*cpu->A == 42);
}

void test_alu_jmp(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->IR[1] = 0x34;
    *cpu->IR[2] = 0x12;
    alu_jmp(cpu, msg, sizeof(msg));
    assert(*cpu->PC[0] == 0x34);
    assert(*cpu->PC[1] == 0x12);
}

void test_alu_jc0_jc1(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->IR[1] = 0x10;
    *cpu->IR[2] = 0x00;
    cpu_set_flag(cpu, FLAG_POS_CARRY, 0);
    alu_jc0(cpu, msg, sizeof(msg));
    assert(*cpu->PC[0] == 0x10);

    cpu_reset(cpu);
    *cpu->IR[1] = 0x10;
    *cpu->IR[2] = 0x00;
    cpu_set_flag(cpu, FLAG_POS_CARRY, 1);
    alu_jc0(cpu, msg, sizeof(msg));
    assert(*cpu->PC[0] == 0x00);

    cpu_reset(cpu);
    *cpu->IR[1] = 0x10;
    *cpu->IR[2] = 0x00;
    cpu_set_flag(cpu, FLAG_POS_CARRY, 1);
    alu_jc1(cpu, msg, sizeof(msg));
    assert(*cpu->PC[0] == 0x10);
}

void test_alu_ja0_ja1(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->IR[1] = 0x10;
    *cpu->IR[2] = 0x00;
    *cpu->A = 0;
    alu_ja0(cpu, msg, sizeof(msg));
    assert(*cpu->PC[0] == 0x10);

    cpu_reset(cpu);
    *cpu->IR[1] = 0x10;
    *cpu->IR[2] = 0x00;
    *cpu->A = 1;
    alu_ja0(cpu, msg, sizeof(msg));
    assert(*cpu->PC[0] == 0x00);

    cpu_reset(cpu);
    *cpu->IR[1] = 0x10;
    *cpu->IR[2] = 0x00;
    *cpu->A = 1;
    alu_ja1(cpu, msg, sizeof(msg));
    assert(*cpu->PC[0] == 0x10);
}

void test_alu_cll_ret(CPU *cpu) {
    cpu_init(cpu);
    cpu_reset(cpu);
    char msg[CPU_MSG_SIZE];
    *cpu->PC[0] = 0x05;
    *cpu->PC[1] = 0x00;
    *cpu->IR[1] = 0x20;
    *cpu->IR[2] = 0x00;
    alu_cll(cpu, msg, sizeof(msg));
    assert(*cpu->PC[0] == 0x20);
    alu_ret(cpu, msg, sizeof(msg));
    assert(*cpu->PC[0] == 0x05);
}
