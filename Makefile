CC := gcc
CFLAGS := -D_POSIX_C_SOURCE=200809L \
		  -std=c2x -Wall -Wextra -Wpedantic -Wunused-function -O2
LDFLAGS := 

TARGET := bin/kone

SRCS := $(wildcard src/*.c)
OBJS := $(patsubst src/%.c, obj/%.o, $(SRCS))

EXAMPLE_SRCS := $(wildcard examples/*.kasm)
EXAMPLE_TARGETS := $(patsubst examples/%.kasm, bin/%.bin, $(EXAMPLE_SRCS))

$(shell mkdir -p bin obj)

all: $(TARGET) $(EXAMPLE_TARGETS)

$(TARGET): $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) -o $@

obj/%.o: src/%.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf bin/ obj/

format:
	clang-format -i $$(find . -name '*.c' -or -name '*.h')

check: format all

bin/%.bin: examples/%.kasm
	python tools/kasm.py -i $< -o $@

examples: $(EXAMPLE_TARGETS)

cleanExamples:
	rm -f bin/*.bin

.PHONY: all clean
