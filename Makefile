CC := gcc
CFLAGS := -D_POSIX_C_SOURCE=200809L \
		  -std=c2x -Wall -Wextra -Wpedantic -Wunused-function -O2
LDFLAGS := 

TARGET := bin/kone

SRCS := $(wildcard src/*.c)
OBJS := $(patsubst src/%.c, obj/%.o, $(SRCS))

$(shell mkdir -p bin obj)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) -o $@

obj/%.o: src/%.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf bin/ obj/

format:
	clang-format -i $$(find . -name '*.c' -or -name '*.h')

check: format all

.PHONY: all clean
