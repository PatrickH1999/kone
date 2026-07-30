#ifndef KEYBOARD_FUNCTIONS_H
#define KEYBOARD_FUNCTIONS_H

#include <termios.h>
#include <unistd.h>

#include "cpu_struct.h"

#define KEYBOARD_ASCII_LO 32
#define KEYBOARD_ASCII_HI 255
#define REG_ID_KEYBOARD_CHAR 17 // CPU register ID for receive char
#define REG_ID_KEYBOARD_SET 16  // CPU register ID for receive set bit

void keyboard_init();
void keyboard_cleanup(int sig);
int keyboard_get_char();
void keyboard_push_cpu(CPU *cpu);

#endif
