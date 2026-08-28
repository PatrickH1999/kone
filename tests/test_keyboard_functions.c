#include "test_keyboard_functions.h"

static CPU cpu;
static int stdin_backup;

static void setup() {
    cpu_init(&cpu);
    cpu_reset(&cpu);
}

// Redirects STDIN_FILENO to a pipe pre-loaded with byte `c`, so
// keyboard_get_char() reads it back via read() instead of a real terminal.
static void feed_stdin_byte(unsigned char c) {
    int pipefd[2];
    pipe(pipefd);
    write(pipefd[1], &c, 1);
    close(pipefd[1]);
    dup2(pipefd[0], STDIN_FILENO);
    close(pipefd[0]);
}

// Redirects STDIN_FILENO to a pipe with the write end closed, so a read()
// returns 0 (EOF) immediately instead of blocking, simulating "no key
// pressed".
static void feed_stdin_empty() {
    int pipefd[2];
    pipe(pipefd);
    close(pipefd[1]);
    dup2(pipefd[0], STDIN_FILENO);
    close(pipefd[0]);
}

int main() {
    stdin_backup = dup(STDIN_FILENO);

    TEST_MODULE_BEGIN("keyboard_functions", 6);
    RUN_TEST(test_keyboard_get_char_reads_available_byte);
    RUN_TEST(test_keyboard_get_char_returns_neg1_when_no_input);
    RUN_TEST(test_keyboard_push_cpu_sets_char_in_range);
    RUN_TEST(test_keyboard_push_cpu_replaces_out_of_range_char);
    RUN_TEST(test_keyboard_push_cpu_passes_backspace_through);
    RUN_TEST(test_keyboard_push_cpu_no_input_leaves_registers_unset);
    TEST_MODULE_END("keyboard_functions", 6);

    dup2(stdin_backup, STDIN_FILENO);
    close(stdin_backup);
    return TEST_EXIT_CODE;
}

void test_keyboard_get_char_reads_available_byte() {
    feed_stdin_byte('K');
    assert(keyboard_get_char() == 'K');
}

void test_keyboard_get_char_returns_neg1_when_no_input() {
    feed_stdin_empty();
    assert(keyboard_get_char() == -1);
}

void test_keyboard_push_cpu_sets_char_in_range() {
    setup();
    feed_stdin_byte('A');
    keyboard_push_cpu(&cpu);
    assert(cpu.R[REG_ID_KEYBOARD_CHAR] == 'A');
    assert(cpu.R[REG_ID_KEYBOARD_SET] == 1);
}

void test_keyboard_push_cpu_replaces_out_of_range_char() {
    setup();
    feed_stdin_byte(0x01); // below KEYBOARD_ASCII_LO
    keyboard_push_cpu(&cpu);
    assert(cpu.R[REG_ID_KEYBOARD_CHAR] == ' ');
    assert(cpu.R[REG_ID_KEYBOARD_SET] == 1);
}

void test_keyboard_push_cpu_passes_backspace_through() {
    setup();
    feed_stdin_byte(KEYBOARD_ASCII_BS); // below KEYBOARD_ASCII_LO, but kept
    keyboard_push_cpu(&cpu);
    assert(cpu.R[REG_ID_KEYBOARD_CHAR] == KEYBOARD_ASCII_BS);
    assert(cpu.R[REG_ID_KEYBOARD_SET] == 1);
}

void test_keyboard_push_cpu_no_input_leaves_registers_unset() {
    setup();
    feed_stdin_empty();
    keyboard_push_cpu(&cpu);
    assert(cpu.R[REG_ID_KEYBOARD_CHAR] == 0);
    assert(cpu.R[REG_ID_KEYBOARD_SET] == 0);
}
