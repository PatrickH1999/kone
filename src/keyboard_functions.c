#include "keyboard_functions.h"

#include <stdlib.h>

static struct termios g_orig_termios;

void keyboard_init() {
    tcgetattr(STDIN_FILENO, &g_orig_termios);
    struct termios raw = g_orig_termios;
    raw.c_lflag &= ~(ICANON | ECHO);
    raw.c_cc[VMIN] = 0;
    raw.c_cc[VTIME] = 0;
    tcsetattr(STDIN_FILENO, TCSANOW, &raw);
}

void keyboard_cleanup(const int sig) {
    (void)sig;
    tcsetattr(STDIN_FILENO, TCSANOW, &g_orig_termios);
    exit(0);
}

int keyboard_get_char() {
    unsigned char char_;
    const int n = read(STDIN_FILENO, &char_, 1);
    return n == 1 ? char_ : -1;
}

void keyboard_push_cpu(CPU *cpu) {
    int char_ = keyboard_get_char();
    if (char_ != -1) {
        if ((KEYBOARD_ASCII_LO <= char_ && char_ <= KEYBOARD_ASCII_HI) ||
            char_ == KEYBOARD_ASCII_BS) {
            cpu->R[REG_ID_KEYBOARD_CHAR] = char_;
        } else {
            cpu->R[REG_ID_KEYBOARD_CHAR] = ' ';
        }
        cpu->R[REG_ID_KEYBOARD_SET] = 1;
    }
}
