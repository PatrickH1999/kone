CC := gcc

# Preprocessor definitions (-D, -I) are kept separate from CFLAGS by convention.
CPPFLAGS := -D_POSIX_C_SOURCE=200809L -D_GNU_SOURCE

# Compiler flags. These warning flags are intentionally strict -- do not relax them.
CFLAGS := -std=c2x -Wall -Wextra -Wpedantic -Wunused-function -O2

# Auto-generate header dependencies alongside each object file (see -include below).
DEPFLAGS = -MMD -MP

LDFLAGS :=

TARGET := bin/kone

SRCS := $(wildcard src/*.c)
OBJS := $(patsubst src/%.c, obj/%.o, $(SRCS))
DEPS := $(OBJS:.o=.d)

TEST_SRCS := $(wildcard tests/*.c)
TEST_BINS := $(patsubst tests/%.c, bin/%, $(TEST_SRCS))
TEST_OBJS := $(filter-out obj/kone.o, $(OBJS)) # exclude kone.c, it defines main()

EXAMPLE_SRCS := $(wildcard examples/*.kasm)
EXAMPLE_TARGETS := $(patsubst examples/%.kasm, bin/%.bin, $(EXAMPLE_SRCS))

# kasm assembler subproject: built by its own Makefile into tools/kasm.
KASM_DIR := src/kasm
KASM := tools/kasm
KASM_SRCS := $(wildcard $(KASM_DIR)/*.c) $(wildcard $(KASM_DIR)/*.h)

# Install location, overridable via `make install PREFIX=...` or `DESTDIR=...`.
PREFIX ?= $(HOME)/.local

# Ensure output directories exist before any recipe runs.
$(shell mkdir -p bin obj)

.PHONY: all kone kasm debug examples test install clean format check

all: $(TARGET) $(KASM) $(EXAMPLE_TARGETS)

kone: $(TARGET)

kasm: $(KASM)

$(KASM): $(KASM_SRCS)
	$(MAKE) -C $(KASM_DIR)

$(TARGET): $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) -o $@

obj/%.o: src/%.c | obj bin
	$(CC) $(CPPFLAGS) $(CFLAGS) $(DEPFLAGS) -c $< -o $@

obj bin:
	mkdir -p $@

# Debug build: no optimization, debug symbols, DEBUG macro defined.
debug: CFLAGS += -g -O0 -DDEBUG
debug: clean all

examples: $(EXAMPLE_TARGETS)

bin/%.bin: examples/%.kasm $(KASM)
	$(KASM) -i $< -o $@

test: $(TEST_BINS)
	@for t in $(TEST_BINS); do \
		./$$t && echo "$$t OK" || echo "$$t FAILED"; \
	done

bin/%: tests/%.c $(TEST_OBJS)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(TEST_OBJS) -o $@

install: $(TARGET) examples
	mkdir -p $(PREFIX)/bin
	install -Dm755 $(TARGET) $(PREFIX)/bin/kone

clean:
	rm -rf bin/ obj/
	$(MAKE) -C $(KASM_DIR) clean
	rm -f $(KASM)
	rm -f $(PREFIX)/bin/kone

format:
	clang-format -i $$(find . -name '*.c' -or -name '*.h')

check: format all

# Include auto-generated header dependencies, if present.
-include $(DEPS)
