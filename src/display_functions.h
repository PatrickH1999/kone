#ifndef DISPLAY_FUNCTIONS_H
#define DISPLAY_FUNCTIONS_H

#include "cpu_struct.h"
#include "display_struct.h"

void display_print(Display *display);
void display_fetch(CPU *cpu, Display *display);

#endif
