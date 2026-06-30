#include "test_alu_functions.h"

int main() {
    CPU cpu;
    Args args = {.v = 0};

    printf("\n\tTesting alu_functions\n");
    test_alu_not(&cpu, &args);
    test_alu_bsl(&cpu, &args);
    test_alu_bsr(&cpu, &args);
    test_alu_brl(&cpu, &args);
    test_alu_brr(&cpu, &args);
    test_alu_ldi(&cpu, &args);
    test_alu_ldr_str(&cpu, &args);
    test_alu_orr(&cpu, &args);
    test_alu_and(&cpu, &args);
    test_alu_xor(&cpu, &args);
    test_alu_add(&cpu, &args);
    test_alu_ldm_stm(&cpu, &args);
    test_alu_psh_pop(&cpu, &args);
    test_alu_jmp(&cpu, &args);
    test_alu_jc0_jc1(&cpu, &args);
    test_alu_ja0_ja1(&cpu, &args);
    test_alu_cll_ret(&cpu, &args);
    printf("\tALL PASS: alu_functions\n");
    return 0;
}

void test_alu_not(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->A = 0b10101010;
    alu_not(cpu, args);
    assert(*cpu->A == 0b01010101);
    *cpu->A = 0x00;
    alu_not(cpu, args);
    assert(*cpu->A == 0xFF);
    printf("\t\tPASS: alu_not\n");
}

void test_alu_bsl(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->A = 0b00000001;
    alu_bsl(cpu, args);
    assert(*cpu->A == 0b00000010);
    *cpu->A = 0b10000000;
    alu_bsl(cpu, args);
    assert(*cpu->A == 0b00000000);
    printf("\t\tPASS: alu_bsl\n");
}

void test_alu_bsr(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->A = 0b00000010;
    alu_bsr(cpu, args);
    assert(*cpu->A == 0b00000001);
    *cpu->A = 0b00000001;
    alu_bsr(cpu, args);
    assert(*cpu->A == 0b00000000);
    printf("\t\tPASS: alu_bsr\n");
}

void test_alu_brl(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->A = 0b10000000;
    alu_brl(cpu, args);
    assert(*cpu->A == 0b00000001);
    *cpu->A = 0b00000001;
    alu_brl(cpu, args);
    assert(*cpu->A == 0b00000010);
    printf("\t\tPASS: alu_brl\n");
}

void test_alu_brr(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->A = 0b00000001;
    alu_brr(cpu, args);
    assert(*cpu->A == 0b10000000);
    *cpu->A = 0b00000010;
    alu_brr(cpu, args);
    assert(*cpu->A == 0b00000001);
    printf("\t\tPASS: alu_brr\n");
}

void test_alu_ldi(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->IR[1] = 42;
    alu_ldi(cpu, args);
    assert(*cpu->A == 42);
    *cpu->IR[1] = 0xFF;
    alu_ldi(cpu, args);
    assert(*cpu->A == 0xFF);
    printf("\t\tPASS: alu_ldi\n");
}

void test_alu_ldr_str(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->A = 99;
    *cpu->IR[1] = 0;
    alu_str(cpu, args);
    assert(cpu->R[0] == 99);
    *cpu->A = 0;
    alu_ldr(cpu, args);
    assert(*cpu->A == 99);
    printf("\t\tPASS: alu_ldr_str\n");
}

void test_alu_orr(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->A = 0b10100000;
    cpu->R[0] = 0b00001010;
    *cpu->IR[1] = 0;
    alu_orr(cpu, args);
    assert(*cpu->A == 0b10101010);
    printf("\t\tPASS: alu_orr\n");
}

void test_alu_and(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->A = 0b11110000;
    cpu->R[0] = 0b10101010;
    *cpu->IR[1] = 0;
    alu_and(cpu, args);
    assert(*cpu->A == 0b10100000);
    printf("\t\tPASS: alu_and\n");
}

void test_alu_xor(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->A = 0b11110000;
    cpu->R[0] = 0b10101010;
    *cpu->IR[1] = 0;
    alu_xor(cpu, args);
    assert(*cpu->A == 0b01011010);
    printf("\t\tPASS: alu_xor\n");
}

void test_alu_add(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->A = 10;
    cpu->R[0] = 5;
    *cpu->IR[1] = 0;
    alu_add(cpu, args);
    assert(*cpu->A == 15);
    assert(!cpu_get_flag(cpu, FLAG_POS_CARRY));
    *cpu->A = 0xFF;
    cpu->R[0] = 1;
    alu_add(cpu, args);
    assert(*cpu->A == 0x00);
    assert(cpu_get_flag(cpu, FLAG_POS_CARRY));
    printf("\t\tPASS: alu_add\n");
}

void test_alu_ldm_stm(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->A = 77;
    *cpu->IR[1] = 0x00;
    *cpu->IR[2] = 0x10;
    alu_stm(cpu, args);
    *cpu->A = 0;
    alu_ldm(cpu, args);
    assert(*cpu->A == 77);
    printf("\t\tPASS: alu_ldm_stm\n");
}

void test_alu_psh_pop(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->A = 42;
    alu_psh(cpu, args);
    *cpu->A = 0;
    alu_pop(cpu, args);
    assert(*cpu->A == 42);
    printf("\t\tPASS: alu_psh_pop\n");
}

void test_alu_jmp(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->IR[1] = 0x34;
    *cpu->IR[2] = 0x12;
    alu_jmp(cpu, args);
    assert(*cpu->PC[0] == 0x34);
    assert(*cpu->PC[1] == 0x12);
    printf("\t\tPASS: alu_jmp\n");
}

void test_alu_jc0_jc1(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->IR[1] = 0x10;
    *cpu->IR[2] = 0x00;
    cpu_set_flag(cpu, FLAG_POS_CARRY, 0);
    alu_jc0(cpu, args);
    assert(*cpu->PC[0] == 0x10);

    cpu_reset(cpu);
    *cpu->IR[1] = 0x10;
    *cpu->IR[2] = 0x00;
    cpu_set_flag(cpu, FLAG_POS_CARRY, 1);
    alu_jc0(cpu, args);
    assert(*cpu->PC[0] == 0x00);

    cpu_reset(cpu);
    *cpu->IR[1] = 0x10;
    *cpu->IR[2] = 0x00;
    cpu_set_flag(cpu, FLAG_POS_CARRY, 1);
    alu_jc1(cpu, args);
    assert(*cpu->PC[0] == 0x10);
    printf("\t\tPASS: alu_jc0_jc1\n");
}

void test_alu_ja0_ja1(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->IR[1] = 0x10;
    *cpu->IR[2] = 0x00;
    *cpu->A = 0;
    alu_ja0(cpu, args);
    assert(*cpu->PC[0] == 0x10);

    cpu_reset(cpu);
    *cpu->IR[1] = 0x10;
    *cpu->IR[2] = 0x00;
    *cpu->A = 1;
    alu_ja0(cpu, args);
    assert(*cpu->PC[0] == 0x00);

    cpu_reset(cpu);
    *cpu->IR[1] = 0x10;
    *cpu->IR[2] = 0x00;
    *cpu->A = 1;
    alu_ja1(cpu, args);
    assert(*cpu->PC[0] == 0x10);
    printf("\t\tPASS: alu_ja0_ja1\n");
}

void test_alu_cll_ret(CPU *cpu, Args *args) {
    cpu_init(cpu);
    cpu_reset(cpu);
    *cpu->PC[0] = 0x05;
    *cpu->PC[1] = 0x00;
    *cpu->IR[1] = 0x20;
    *cpu->IR[2] = 0x00;
    alu_cll(cpu, args);
    assert(*cpu->PC[0] == 0x20);
    alu_ret(cpu, args);
    assert(*cpu->PC[0] == 0x05);
    printf("\t\tPASS: alu_cll_ret\n");
}
