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

# Library sources are pulled in via '.include'; kasm emits no dependency
# files, so every example is rebuilt whenever any of them changes.
KLIB_SRCS := $(wildcard klib/*.kasm klib/*/*.kasm)

KLIB_TEST_SRCS := $(wildcard tests/klib/*.kasm)
KLIB_TEST_BINS := $(patsubst tests/klib/test_%.kasm, bin/test_klib_%.bin, \
                            $(KLIB_TEST_SRCS))

# The kone vm never halts on its own, so a klib test is run in the background
# and its display output is polled for the summary line until this many
# seconds have passed.
KLIB_TEST_TIMEOUT := 20

KASM_DIR := src/kasm
KASM := bin/kasm
KASM_SRCS := $(wildcard $(KASM_DIR)/*.c) $(wildcard $(KASM_DIR)/*.h)
KASM_OBJS := obj/assembler.o obj/isa.o obj/symtab.o
KASM_TEST_BIN := bin/test_kasm

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

bin/%.bin: examples/%.kasm $(KLIB_SRCS) $(KASM)
	$(KASM) -i $< -o $@

bin/test_klib_%.bin: tests/klib/test_%.kasm $(KLIB_SRCS) $(KASM)
	$(KASM) -i $< -o $@

test: $(TEST_BINS) $(KASM_TEST_BIN) $(KLIB_TEST_BINS) $(TARGET)
	@passed=0; failed=0; \
	if [ -t 1 ]; then bld='\033[1m'; grn='\033[38;2;0;255;0m'; red='\033[38;2;255;0;0m'; \
	dflt='\033[39m'; rst='\033[0m'; dgrn='\033[38;2;0;200;0m'; \
	dred='\033[38;2;200;0;0m'; wht='\033[38;2;200;200;200m'; \
	else bld=''; grn=''; red=''; dflt=''; rst=''; dgrn=''; dred=''; wht=''; fi; \
	printf "\n"; \
	for t in $(TEST_BINS) $(KASM_TEST_BIN); do \
		if ./$$t; then \
			printf "$${bld}$${grn}[ PASS ] $${dflt}%s$${rst}\n\n" "$$t"; \
			passed=$$((passed + 1)); \
		else \
			printf "$${bld}$${red}[ FAIL ] $${dflt}%s$${rst}\n\n" "$$t"; \
			failed=$$((failed + 1)); \
		fi; \
	done; \
	klib_failed=0; \
	for t in $(KLIB_TEST_BINS); do \
		out=$$t.out; \
		./$(TARGET) -b $$t < /dev/null > $$out 2>&1 & \
		pid=$$!; \
		i=0; \
		while [ $$i -lt $$(($(KLIB_TEST_TIMEOUT) * 5)) ]; do \
			if grep -aqE 'ALL PASS|FAILED' $$out; then break; fi; \
			i=$$((i + 1)); \
			sleep 0.2; \
		done; \
		sleep 0.4; \
		pkill -P $$pid > /dev/null 2>&1; \
		kill $$pid > /dev/null 2>&1; \
		wait $$pid 2>/dev/null; \
		a='BEGIN{RS="\033\\[3J"}{p=c;c=$$0}END{printf "%s",p}'; \
		awk "$$a" $$out | grep -oE '(PASS|FAIL):[a-z0-9_]+' | \
		while IFS=: read -r r c; do \
			if [ "$$r" = PASS ]; then col=$$dgrn; else col=$$dred; fi; \
			printf "$$col[ %s ] $${rst}$${wht}%s$${rst}\n" "$$r" "$$c"; \
		done; \
		if ! grep -aq 'ALL PASS' $$out; then \
			if ! grep -aq 'FAILED' $$out; then \
				printf "$$dred[ FAIL ] $${rst}$${wht}%s: no summary within %ss$${rst}\n" \
					"$$t" "$(KLIB_TEST_TIMEOUT)"; \
			fi; \
			klib_failed=$$((klib_failed + 1)); \
		fi; \
		rm -f $$out; \
	done; \
	if [ $$klib_failed -eq 0 ]; then \
		printf "$${bld}$${grn}[ PASS ] $${dflt}klib/math$${rst}\n\n"; \
		passed=$$((passed + 1)); \
	else \
		printf "$${bld}$${red}[ FAIL ] $${dflt}klib/math$${rst}\n\n"; \
		failed=$$((failed + 1)); \
	fi; \
	echo; \
	if [ $$failed -gt 0 ]; then \
		printf "$${bld}$${red}[ FAIL ] $${dflt}%d/%d test binaries passed$${rst}\n" \
			"$$passed" "$$((passed + failed))"; \
		exit 1; \
	else \
		printf "$${bld}$${grn}[ PASS ] $${dflt}%d/%d test binaries passed$${rst}\n" \
			"$$passed" "$$((passed + failed))"; \
	fi

bin/%: tests/%.c $(TEST_OBJS)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(TEST_OBJS) -o $@

$(KASM_TEST_BIN): tests/kasm/test_kasm.c $(KASM)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(KASM_OBJS) -o $@

install: $(TARGET) $(KASM) examples
	mkdir -p $(PREFIX)/bin
	install -Dm755 $(TARGET) $(PREFIX)/bin/kone
	install -Dm755 $(KASM) $(PREFIX)/bin/kasm

clean:
	$(MAKE) -C $(KASM_DIR) clean
	rm -rf bin/ obj/
	rm -f $(PREFIX)/bin/kone $(PREFIX)/bin/kasm

format:
	clang-format -i $$(find . -name '*.c' -or -name '*.h')

check: format all

-include $(DEPS)
