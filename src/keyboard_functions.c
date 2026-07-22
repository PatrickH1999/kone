#include "keyboard_functions.h"

int keyboard_get_char() {
    struct termios old, new;
    tcgetattr(STDIN_FILENO, &old);
    new = old;
    new.c_lflag &= ~(ICANON | ECHO);
    new.c_cc[VMIN] = 0;
    new.c_cc[VTIME] = 0;
    tcsetattr(STDIN_FILENO, TCSANOW, &new);
    int char_ = getchar();
    tcsetattr(STDIN_FILENO, TCSANOW, &old);
    return char_;
}

void keyboard_push_cpu(CPU *cpu) {
    int char_ = keyboard_get_char();
    if (char_ != -1) {
        if (KBRD_ASCII_LO <= char_ && char_ <= KBRD_ASCII_HI) {
            cpu->R[REG_ID_KBRD_CHAR] = char_;
        } else {
            cpu->R[REG_ID_KBRD_CHAR] = ' ';
        }
        cpu->R[REG_ID_KBRD_SET] = 1;
    }
}
