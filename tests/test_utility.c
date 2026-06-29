#include "test_utility.h"

void test_addr_convert_8_to_16() {
    uint16_t result;
    uint8_t bytes[2] = {0x34, 0x12};
    addr_convert_8_to_16(&result, bytes);
    assert(result == 0x1234);
    uint8_t zeros[2] = {0x00, 0x00};
    addr_convert_8_to_16(&result, zeros);
    assert(result == 0x0000);
    uint8_t maxes[2] = {0xFF, 0xFF};
    addr_convert_8_to_16(&result, maxes);
    assert(result == 0xFFFF);
    printf("\t\tPASS: addr_convert_8_to_16\n");
}

void test_addr_convert_16_to_8() {
    uint8_t bytes[2];
    addr_convert_16_to_8(bytes, 0x1234);
    assert(bytes[0] == 0x34); // low byte
    assert(bytes[1] == 0x12); // high byte
    addr_convert_16_to_8(bytes, 0x0000);
    assert(bytes[0] == 0x00);
    assert(bytes[1] == 0x00);
    addr_convert_16_to_8(bytes, 0xFFFF);
    assert(bytes[0] == 0xFF);
    assert(bytes[1] == 0xFF);
    printf("\t\tPASS: addr_convert_16_to_8\n");
}

void test_brl8() {
    assert(brl8(0b00000001, 1) == 0b00000010);
    assert(brl8(0b10000000, 1) == 0b00000001); // wraps
    assert(brl8(0b00000001, 8) == 0b00000001); // full rotation
    printf("\t\tPASS: brl8\n");
}

void test_brr8() {
    assert(brr8(0b00000010, 1) == 0b00000001);
    assert(brr8(0b00000001, 1) == 0b10000000); // wraps
    assert(brr8(0b00000001, 8) == 0b00000001); // full rotation
    printf("\t\tPASS: brr8\n");
}

void test_get_pos_first_1_in_byte() {
    assert(get_pos_first_1_in_byte(0b10000000) == 7);
    assert(get_pos_first_1_in_byte(0b00000001) == 0);
    assert(get_pos_first_1_in_byte(0b00010000) == 4);
    assert(get_pos_first_1_in_byte(0b00000000) == -1);
    assert(get_pos_first_1_in_byte(0b11111111) == 7);
    printf("\t\tPASS: get_pos_first_1_in_byte\n");
}

int main() {
    printf("\n\tTesting test/test_utility\n");
    test_addr_convert_8_to_16();
    test_addr_convert_16_to_8();
    test_brl8();
    test_brr8();
    test_get_pos_first_1_in_byte();
    printf("\tALL PASS: test/test_utility\n");
    return 0;
}
