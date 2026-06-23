#include "display_functions.h"

void display_print(Display *display) {
    for (int i = 0; i < DISP_NROWS; i++) { // i:
        for (int j = 0; j < DISP_NCOLS; j++) {
            // i: relative to DRP
            // abs_i: relative to address 0 in display memory
            uint8_t abs_i = (display->DRP + i) % DISP_NROWS;
            uint8_t char_ = display->DM[abs_i * DISP_NCOLS + j];
            if (DISP_ASCII_LO <= char_ && char_ >= DISP_ASCII_HI) {
                printf("%c", char_);
            } else {
                printf(" ");
            }
        }
        printf("\n");
    }
}

void display_fetch(CPU *cpu, Display *display) {
    // fetch character and set-bit from cpu
    // if set: push them to display memory (DM), unset set-bit
}
