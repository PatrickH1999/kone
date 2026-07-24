CC := gcc

CPPFLAGS := -D_POSIX_C_SOURCE=200809L -D_GNU_SOURCE

CFLAGS := -std=c2x -Wall -Wextra -Wpedantic -Wunused-function -O2

DEPFLAGS = -MMD -MP

LDFLAGS :=

TARGET := bin/kone

SRCS := $(wildcard src/*.c)
OBJS := $(patsubst src/%.c, obj/%.o, $(SRCS))
DEPS := $(OBJS:.o=.d)

TEST_SRCS := $(wildcard tests/*.c)
TEST_BINS := $(patsubst tests/%.c, bin/%, $(TEST_SRCS))
TEST_OBJS := $(filter-out obj/kone.o, $(OBJS))

EXAMPLE_SRCS := $(wildcard examples/*.kasm)
EXAMPLE_TARGETS := $(patsubst examples/%.kasm, bin/%.bin, $(EXAMPLE_SRCS))

KASM_DIR := src/kasm
KASM := bin/kasm
KASM_SRCS := $(wildcard $(KASM_DIR)/*.c) $(wildcard $(KASM_DIR)/*.h)

PREFIX ?= $(HOME)/.local

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

debug: CFLAGS += -g -O0 -DDEBUG
debug: clean all

examples: $(EXAMPLE_TARGETS)

bin/%.bin: examples/%.kasm $(KASM)
	$(KASM) -i $< -o $@

test: $(TEST_BINS)
	@passed=0; failed=0; \
	if [ -t 1 ]; then grn='\033[0;32m'; red='\033[0;31m'; rst='\033[0m'; \
	else grn=''; red=''; rst=''; fi; \
	printf "\n"; \
	for t in $(TEST_BINS); do \
		if ./$$t; then \
			printf "$${grn}[  PASSED  ]$${rst} %s\n\n" "$$t"; \
			passed=$$((passed + 1)); \
		else \
			printf "$${red}[  FAILED  ]$${rst} %s\n\n" "$$t"; \
			failed=$$((failed + 1)); \
		fi; \
	done; \
	echo; \
	if [ $$failed -gt 0 ]; then \
		printf "$${red}[  FAILED  ]$${rst} %d/%d test binaries passed\n" \
			"$$passed" "$$((passed + failed))"; \
		exit 1; \
	else \
		printf "$${grn}[  PASSED  ]$${rst} %d/%d test binaries passed\n" \
			"$$passed" "$$((passed + failed))"; \
	fi

bin/%: tests/%.c $(TEST_OBJS)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(TEST_OBJS) -o $@

install: $(TARGET) examples
	mkdir -p $(PREFIX)/bin
	install -Dm755 $(TARGET) $(PREFIX)/bin/kone

clean:
	$(MAKE) -C $(KASM_DIR) clean
	rm -rf bin/ obj/
	rm -f $(PREFIX)/bin/kone

format:
	clang-format -i $$(find . -name '*.c' -or -name '*.h')

check: format all

-include $(DEPS)
