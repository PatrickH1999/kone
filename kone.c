#include "cpu_struct.h"
#include "cpu_functions.h"

int main() {
    CPU cpu;
    cpu_reset(&cpu);
    cpu.M[0] = 0b10001000;   // load imm "1" into acc
    cpu.M[1] = 0b00000001;   // """
    cpu.M[2] = 0b00011001;   // store acc to reg1
    cpu.M[3] = 0b10001000;   // load imm "0" into acc
    cpu.M[4] = 0b00000000;   // """
    cpu.M[5] = 0b00111001;   // LOOP: add reg1 to acc
    cpu.M[6] = 0b00011000;   // store acc to reg0
    cpu.M[7] = 0b01100000;   // print reg0
    cpu.M[8] = 0b10100000;   // jump to LOOP
    cpu.M[9] = 0b00000101;   // """

    while (true) {
        cpu_fetch(&cpu);
        cpu_decode_exec(&cpu);
    }

    return 0;
}
