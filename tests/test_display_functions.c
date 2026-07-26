#include "test_display_functions.h"

static Display display;
static CPU cpu;
static Args args = {.v = 0};

static void setup() {
    cpu_init(&cpu);
    cpu_reset(&cpu);
    display_reset(&display);
}

int main() {
    TEST_MODULE_BEGIN("display_functions", 6);
    RUN_TEST(test_display_reset);
    RUN_TEST(test_display_push_char_basic);
    RUN_TEST(test_display_push_char_col_wrap);
    RUN_TEST(test_display_push_char_row_wrap);
    RUN_TEST(test_display_fetch_set);
    RUN_TEST(test_display_fetch_no_set);
    TEST_MODULE_END("display_functions", 6);
    return 0;
}

void test_display_reset() {
    setup();
    // fill with junk then reset
    memset(display.DM, 0xFF, sizeof(display.DM));
    display.DRP = 5;
    display.DCP = 10;
    display_reset(&display);
    assert(display.DRP == 0);
    assert(display.DCP == 0);
    for (int i = 0; i < DISP_NROWS * DISP_NCOLS; i++)
        assert(display.DM[i] == 0);
}

void test_display_push_char_basic() {
    setup();
    display_push_char(&display, 'A');
    assert(display.DM[0] == 'A');
    assert(display.DCP == 1);
    assert(display.DRP == 0);
    display_push_char(&display, 'B');
    assert(display.DM[1] == 'B');
    assert(display.DCP == 2);
}

void test_display_push_char_col_wrap() {
    setup();
    // fill entire first row
    for (int j = 0; j < DISP_NCOLS; j++)
        display_push_char(&display, 'X');
    // after last col, DCP should wrap and DRP should advance
    assert(display.DCP == 0);
    assert(display.DRP == 1);
    // next row should be cleared
    int next_row = (0 + 1) % DISP_NROWS;
    for (int j = 0; j < DISP_NCOLS; j++)
        assert(display.DM[next_row * DISP_NCOLS + j] == 0);
}

void test_display_push_char_row_wrap() {
    setup();
    // fill all rows
    for (int i = 0; i < DISP_NROWS * DISP_NCOLS; i++)
        display_push_char(&display, 'Z');
    // DRP and DCP should have wrapped around without crash
    assert(display.DRP < DISP_NROWS);
    assert(display.DCP < DISP_NCOLS);
}

void test_display_fetch_set() {
    setup();
    cpu.R[REG_ID_DISP_CHAR] = 'H';
    cpu.R[REG_ID_DISP_SET] = 1;
    display_fetch(&cpu, &display);
    assert(display.DM[0] == 'H');
    assert(cpu.R[REG_ID_DISP_SET] == 0); // should be cleared
}

void test_display_fetch_no_set() {
    setup();
    cpu.R[REG_ID_DISP_CHAR] = 'X';
    cpu.R[REG_ID_DISP_SET] = 0;
    display_fetch(&cpu, &display);
    assert(display.DM[0] == 0); // nothing pushed
}
