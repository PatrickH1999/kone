#include "display_functions.h"

void display_reset(Display *display) {
    memset(display->DM, 0, sizeof(display->DM));

    display->DRP = 0;
    display->DCP = 0;
}

void display_print(const Display *display) {
    for (int i = 0; i < DISP_NROWS; i++) { // i:
        for (int j = 0; j < DISP_NCOLS; j++) {
            // i: relative to DRP
            const uint8_t char_ = display->DM[i * DISP_NCOLS + j];
            if (DISP_ASCII_LO <= char_ && char_ <= DISP_ASCII_HI) {
                printf("%c", char_);
            } else {
                printf(" ");
            }
        }
        printf("\n");
    }
}

void display_push_char(Display *display, const char char_) {
    uint16_t DP16 = (display->DRP * DISP_NCOLS) + display->DCP;
    display->DM[DP16] = char_;
    if (display->DCP < (DISP_NCOLS - 1)) {
        (display->DCP)++;
    } else { // Case: Last column
        if (display->DRP < (DISP_NROWS - 1)) {
            display->DCP = 0;
            display->DRP = (display->DRP + 1) % DISP_NROWS;
            // clean up next row:
            for (int j = 0; j < DISP_NCOLS; j++) {
                DP16 = (display->DRP * DISP_NCOLS) + j;
                display->DM[DP16] = 0;
            }
        } else { // Case: Last row (and last column)
            display->DCP = 0;
            display->DRP = 0;
            memset(display->DM, 0, sizeof(display->DM));
        }
    }
}

void display_fetch(CPU *cpu, Display *display) {
    if (cpu->R[REG_ID_DISP_SET] != 0) {
        const char char_ = cpu->R[REG_ID_DISP_CHAR];
        display_push_char(display, char_);
        cpu->R[REG_ID_DISP_SET] = 0;
    }
}
