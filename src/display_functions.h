#ifndef DISPLAY_FUNCTIONS_H
#define DISPLAY_FUNCTIONS_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cpu_struct.h"
#include "display_struct.h"

void display_reset(Display *display);
void display_print(const Display *display);
void display_push_char(Display *display, char char_);
void display_fetch(CPU *cpu, Display *display);
void display_cleanup(int sig);

#endif
