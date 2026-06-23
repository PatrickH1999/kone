#ifndef DISPLAY_STRUCT_H
#define DISPLAY_STRUCT_H

#include <stdint.h>

#define DISP_NCOLS 40
#define DISP_NROWS 24
#define DISP_ASCII_LO 32    // Lower limit of ASCII printable chars (incl.)
#define DISP_ASCII_HI 255   // Upper limit of ASCII printable chars (incl.)
#define REG_ID_DISP_CHAR 19 // CPU register ID for send char
#define REG_ID_DISP_SET 18  // CPU register ID for send set bit

typedef struct {
    uint8_t DM[DISP_NROWS * DISP_NCOLS]; // display memory

    uint8_t DRP; // display row pointer
    uint8_t DCP; // display column pointer
} Display;

#endif
