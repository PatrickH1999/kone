CC := gcc
CFLAGS := -D_DEFAULT_SOURCE -D_POSIX_C_SOURCE=200809L \
		  -std=c2x -Wall -Wextra -Wpedantic -Wunused-function -O2
LDFLAGS :=

TARGET := ../../bin/kasm

SRCS := $(wildcard *.c)
OBJS := $(patsubst %.c, ../../obj/%.o, $(SRCS))

$(shell mkdir -p ../../bin ../../obj)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) -o $@

../../obj/%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)

format:
	clang-format -i *.c *.h

.PHONY: all clean format
