CC := gcc
CFLAGS := -D_POSIX_C_SOURCE=200809L \
		  -std=c2x -Wall -Wextra -Wpedantic -Wunused-function -O2
LDFLAGS := 

TARGET := bin/kone

SRCS := $(wildcard src/*.c)
OBJS := $(patsubst src/%.c, obj/%.o, $(SRCS))

TEST_SRCS := $(wildcard tests/*.c)
TEST_BINS := $(patsubst tests/%.c, bin/%, $(TEST_SRCS))
TEST_OBJS := $(filter-out obj/kone.o, $(OBJS))

EXAMPLE_SRCS := $(wildcard examples/*.kasm)
EXAMPLE_TARGETS := $(patsubst examples/%.kasm, bin/%.bin, $(EXAMPLE_SRCS))

$(shell mkdir -p bin obj)

all: $(TARGET) $(EXAMPLE_TARGETS)

clean:
	rm -rf bin/ obj/

format:
	clang-format -i $$(find . -name '*.c' -or -name '*.h')

test: $(TEST_BINS)
	@for t in $(TEST_BINS); do \
		./$$t && echo "$$t OK" || echo "$$t FAILED"; \
	done

check: format all

$(TARGET): $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) -o $@

obj/%.o: src/%.c
	$(CC) $(CFLAGS) -c $< -o $@

bin/%.bin: examples/%.kasm
	python tools/kasm.py -i $< -o $@

bin/%: tests/%.c $(TEST_OBJS)
	$(CC) $(CFLAGS) $< $(TEST_OBJS) -o $@

examples: $(EXAMPLE_TARGETS)

.PHONY: all clean
