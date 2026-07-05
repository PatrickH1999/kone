#include "display_functions.h"

void display_reset(Display *display) {
    memset(display->DM, 0, sizeof(display->DM));

    display->DRP = 0;
    display->DCP = 0;
}

void display_print(Display *display) {
    printf("\033[3J\033[H\033[2J");        // clear screen
    for (int i = 0; i < DISP_NROWS; i++) { // i:
        for (int j = 0; j < DISP_NCOLS; j++) {
            // i: relative to DRP
            // abs_i: relative to address 0 in display memory
            uint8_t abs_i = (display->DRP + i) % DISP_NROWS;
            uint8_t char_ = display->DM[abs_i * DISP_NCOLS + j];
            if (DISP_ASCII_LO <= char_ && char_ <= DISP_ASCII_HI) {
                printf("%c", char_);
            } else {
                printf(" ");
            }
        }
        printf("\n");
    }
}

void display_push_char(Display *display, char char_) {
    uint16_t DP16 = (display->DRP * DISP_NCOLS) + display->DCP;
    display->DM[DP16] = char_;
    if (display->DCP < (DISP_NCOLS - 1)) {
        (display->DCP)++;
    } else {
        (display->DCP) = (display->DRP + 1) % DISP_NROWS;
        // clean up next row:
        for (int j = 0; j < DISP_NCOLS; j++) {
            DP16 = (display->DRP * DISP_NCOLS) + j;
            display->DM[DP16] = 0;
        }
    }
}

void display_fetch(CPU *cpu, Display *display) {
    if (cpu->R[REG_ID_DISP_SET] != 0) {
        char char_ = cpu->R[REG_ID_DISP_CHAR];
        display_push_char(display, char_);
        cpu->R[REG_ID_DISP_SET] = 0;
    }
}

void display_cleanup(int sig) {
    (void)sig;
    printf("\033[?25h\033[?1049l");
    exit(0);
}
