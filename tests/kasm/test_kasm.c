#include "test_kasm.h"

static char tmpdir[] = "/tmp/kasm_test_XXXXXX";

static char *tmp_path(char *buf, size_t bufsize, const char *name) {
    snprintf(buf, bufsize, "%s/%s", tmpdir, name);
    return buf;
}

static void write_file(const char *path, const char *content) {
    FILE *f = fopen(path, "w");
    assert(f);
    fputs(content, f);
    fclose(f);
}

int main() {
    assert(mkdtemp(tmpdir) != NULL);

    TEST_MODULE_BEGIN("kasm", 10);
    RUN_TEST(test_isa_lookup_known_mnemonic);
    RUN_TEST(test_isa_lookup_unknown_mnemonic);
    RUN_TEST(test_isa_arg_max);
    RUN_TEST(test_isa_instr_size);
    RUN_TEST(test_assemble_no_operand_opcodes);
    RUN_TEST(test_assemble_immediate_operand);
    RUN_TEST(test_assemble_register_operand);
    RUN_TEST(test_assemble_memory_operand_little_endian);
    RUN_TEST(test_assemble_label_resolves_to_address);
    RUN_TEST(test_assemble_include);
    TEST_MODULE_END("kasm", 10);

    rmdir(tmpdir);
    return 0;
}

void test_isa_lookup_known_mnemonic() {
    const Instruction *nop = isa_lookup("NOP");
    assert(nop && nop->opcode == 0x00 && nop->arg_kind == ARG_NONE);
    const Instruction *ldi = isa_lookup("LDI");
    assert(ldi && ldi->opcode == 0x40 && ldi->arg_kind == ARG_IMM);
    const Instruction *jmp = isa_lookup("JMP");
    assert(jmp && jmp->opcode == 0x28 && jmp->takes_label);
}

void test_isa_lookup_unknown_mnemonic() {
    assert(isa_lookup("XYZ") == NULL);
    assert(isa_lookup("") == NULL);
}

void test_isa_arg_max() {
    assert(isa_arg_max(ARG_NONE) == 0);
    assert(isa_arg_max(ARG_REG) == 0x1F);
    assert(isa_arg_max(ARG_IMM) == 0xFF);
    assert(isa_arg_max(ARG_MEM) == 0xFFFF);
}

void test_isa_instr_size() {
    assert(isa_instr_size(ARG_NONE) == 1);
    assert(isa_instr_size(ARG_REG) == 2);
    assert(isa_instr_size(ARG_IMM) == 2);
    assert(isa_instr_size(ARG_MEM) == 3);
}

void test_assemble_no_operand_opcodes() {
    char path[PATH_MAX];
    tmp_path(path, sizeof path, "opcodes.kasm");
    write_file(path, "NOP\nRET\n");

    size_t len;
    uint8_t *code = assemble_file(path, &len);
    assert(len == 2);
    assert(code[0] == 0x00);
    assert(code[1] == 0x0A);
    free(code);
    remove(path);
}

void test_assemble_immediate_operand() {
    char path[PATH_MAX];
    tmp_path(path, sizeof path, "immediate.kasm");
    write_file(path, "LDI 42\n");

    size_t len;
    uint8_t *code = assemble_file(path, &len);
    assert(len == 2);
    assert(code[0] == 0x40);
    assert(code[1] == 0x2A);
    free(code);
    remove(path);
}

void test_assemble_register_operand() {
    char path[PATH_MAX];
    tmp_path(path, sizeof path, "register.kasm");
    write_file(path, "STR 5\n");

    size_t len;
    uint8_t *code = assemble_file(path, &len);
    assert(len == 2);
    assert(code[0] == 0x90);
    assert(code[1] == 0x05);
    free(code);
    remove(path);
}

void test_assemble_memory_operand_little_endian() {
    char path[PATH_MAX];
    tmp_path(path, sizeof path, "memory.kasm");
    write_file(path, "JMP 0x0200\n");

    size_t len;
    uint8_t *code = assemble_file(path, &len);
    assert(len == 3);
    assert(code[0] == 0x28);
    assert(code[1] == 0x00); // low byte
    assert(code[2] == 0x02); // high byte
    free(code);
    remove(path);
}

void test_assemble_label_resolves_to_address() {
    char path[PATH_MAX];
    tmp_path(path, sizeof path, "label.kasm");
    write_file(path, "NOP\nNOP\ntarget: LDI 1\nJMP target\n");

    size_t len;
    uint8_t *code = assemble_file(path, &len);
    // NOP, NOP, LDI 1 (target = 0x0002), JMP 0x0002
    uint8_t expected[] = {0x00, 0x00, 0x40, 0x01, 0x28, 0x02, 0x00};
    assert(len == sizeof expected);
    assert(memcmp(code, expected, len) == 0);
    free(code);
    remove(path);
}

void test_assemble_include() {
    char sub_path[PATH_MAX], main_path[PATH_MAX];
    tmp_path(sub_path, sizeof sub_path, "include_sub.kasm");
    tmp_path(main_path, sizeof main_path, "include_main.kasm");
    write_file(sub_path, "LDI 7\n");
    write_file(main_path, ".include \"include_sub.kasm\"\nNOP\n");

    size_t len;
    uint8_t *code = assemble_file(main_path, &len);
    uint8_t expected[] = {0x40, 0x07, 0x00};
    assert(len == sizeof expected);
    assert(memcmp(code, expected, len) == 0);
    free(code);
    remove(sub_path);
    remove(main_path);
}
