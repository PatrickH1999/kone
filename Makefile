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

# kasm emits no dependency files, so any klib change rebuilds every example.
KLIB_SRCS := $(wildcard klib/*.kasm klib/*/*.kasm)

KLIB_TEST_SRCS := $(wildcard tests/klib/*.kasm)
KLIB_TEST_BINS := $(patsubst tests/klib/test_%.kasm, bin/test_klib_%.bin, \
                            $(KLIB_TEST_SRCS))

# A klib test never halts, so its display is polled for the summary row for
# this long.
KLIB_TEST_TIMEOUT := 20

KASM_DIR := src/kasm
KASM := bin/kasm
KASM_SRCS := $(wildcard $(KASM_DIR)/*.c) $(wildcard $(KASM_DIR)/*.h)
KASM_OBJS := obj/assembler.o obj/isa.o obj/symtab.o
KASM_TEST_BIN := bin/test_kasm

TEST_GROUPS := test-kone test-kasm test-klib

# Shell snippets for the test recipes; TEST_SUMMARY reads the shell variables
# 'group', 'passed' and 'failed'.
TEST_COLORS = if [ -t 1 ]; then \
    bld='\033[1m'; rst='\033[0m'; dflt='\033[39m'; \
    grn='\033[38;2;0;255;0m'; red='\033[38;2;255;0;0m'; \
    dgrn='\033[38;2;0;200;0m'; dred='\033[38;2;200;0;0m'; \
    wht='\033[38;2;200;200;200m'; \
    else bld=''; rst=''; dflt=''; grn=''; red=''; \
    dgrn=''; dred=''; wht=''; fi

TEST_SUMMARY = if [ $$failed -gt 0 ]; then \
    printf "$${bld}$${red}[ FAIL ] $${dflt}%s: %d/%d passed$${rst}\n\n" \
        "$$group" "$$passed" "$$((passed + failed))"; \
    exit 1; \
    else \
    printf "$${bld}$${grn}[ PASS ] $${dflt}%s: %d/%d passed$${rst}\n\n" \
        "$$group" "$$passed" "$$((passed + failed))"; \
    fi

CIRC_SCRIPTS := $(wildcard logisim/python/build_*.py)

PREFIX ?= $(HOME)/.local

$(shell mkdir -p bin obj)

.PHONY: all alu check circ clean debug examples format install kasm kone \
        regfile test $(TEST_GROUPS)

# Main targets.

all: $(TARGET) $(KASM) $(EXAMPLE_TARGETS)

check: format all

# Logisim circuits: every logisim/python/build_*.py writes its own .circ.
circ:
	@for s in $(CIRC_SCRIPTS); do python3 $$s || exit 1; done

alu:
	@python3 logisim/python/build_alu.py

regfile:
	@python3 logisim/python/build_regfile.py

clean:
	$(MAKE) -C $(KASM_DIR) clean
	rm -rf bin/ obj/
	rm -f $(PREFIX)/bin/kone $(PREFIX)/bin/kasm

debug: CFLAGS += -g -O0 -DDEBUG
debug: clean all

examples: $(EXAMPLE_TARGETS)

format:
	clang-format -i $$(find . -name '*.c' -or -name '*.h')

install: $(TARGET) $(KASM) examples
	mkdir -p $(PREFIX)/bin
	install -Dm755 $(TARGET) $(PREFIX)/bin/kone
	install -Dm755 $(KASM) $(PREFIX)/bin/kasm

kasm: $(KASM)

kone: $(TARGET)

# Sub makes, not prerequisites: a failing group must not stop the others.
test:
	@$(TEST_COLORS); \
	passed=0; failed=0; \
	for g in $(TEST_GROUPS); do \
		if $(MAKE) --no-print-directory $$g; then \
			passed=$$((passed + 1)); \
		else \
			failed=$$((failed + 1)); \
		fi; \
	done; \
	group='test groups'; \
	$(TEST_SUMMARY)

# Rules they build through.

$(KASM): $(KASM_SRCS)
	$(MAKE) -C $(KASM_DIR)

$(KASM_TEST_BIN): tests/kasm/test_kasm.c $(KASM)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(KASM_OBJS) -o $@

$(TARGET): $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) -o $@

bin/%: tests/%.c $(TEST_OBJS)
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(TEST_OBJS) -o $@

bin/%.bin: examples/%.kasm $(KLIB_SRCS) $(KASM)
	$(KASM) -i $< -o $@

bin/test_klib_%.bin: tests/klib/test_%.kasm $(KLIB_SRCS) $(KASM)
	$(KASM) -i $< -o $@

obj bin:
	mkdir -p $@

obj/%.o: src/%.c | obj bin
	$(CC) $(CPPFLAGS) $(CFLAGS) $(DEPFLAGS) -c $< -o $@

test-kasm: $(KASM_TEST_BIN)
	@$(TEST_COLORS); \
	passed=0; failed=0; \
	printf "\n"; \
	if ./$(KASM_TEST_BIN); then \
		printf "$${bld}$${grn}[ PASS ] $${dflt}%s$${rst}\n\n" "$(KASM_TEST_BIN)"; \
		passed=1; \
	else \
		printf "$${bld}$${red}[ FAIL ] $${dflt}%s$${rst}\n\n" "$(KASM_TEST_BIN)"; \
		failed=1; \
	fi; \
	group=kasm; \
	$(TEST_SUMMARY)

test-klib: $(KLIB_TEST_BINS) $(TARGET)
	@$(TEST_COLORS); \
	passed=0; failed=0; \
	printf "\n"; \
	for t in $(KLIB_TEST_BINS); do \
		name=$$(basename $$t .bin | sed 's/^test_klib_//'); \
		stem=tests/klib/test_$$name; \
		if [ -f $$stem.in ]; then in=$$stem.in; else in=/dev/null; fi; \
		out=$$t.out; \
		./$(TARGET) -b $$t < $$in > $$out 2>&1 & \
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
		awk "$$a" $$out | sed 's/\x1b\[[0-9;]*[A-Za-z]//g; s/[[:space:]]*$$//' \
			> $$out.frame; \
		grep -oE '(PASS|FAIL):[a-z0-9_]+' $$out.frame | \
		while IFS=: read -r r c; do \
			if [ "$$r" = PASS ]; then col=$$dgrn; else col=$$dred; fi; \
			printf "$$col[ %s ] $${rst}$${wht}%s$${rst}\n" "$$r" "$$c"; \
		done; \
		expect_failed=0; \
		if [ -f $$stem.expect ]; then \
			while IFS= read -r row; do \
				if [ -z "$$row" ]; then continue; fi; \
				if grep -Fxq -- "$$row" $$out.frame; then \
					printf "$$dgrn[ PASS ] $${rst}$${wht}%s_printed_%s$${rst}\n" \
						"$$name" "$$row"; \
				else \
					printf "$$dred[ FAIL ] $${rst}$${wht}%s: no display row '%s'$${rst}\n" \
						"$$name" "$$row"; \
					expect_failed=1; \
				fi; \
			done < $$stem.expect; \
		fi; \
		if ! grep -aq 'ALL PASS' $$out; then \
			if ! grep -aq 'FAILED' $$out; then \
				printf "$$dred[ FAIL ] $${rst}$${wht}%s: no summary within %ss$${rst}\n" \
					"$$t" "$(KLIB_TEST_TIMEOUT)"; \
			fi; \
			failed=$$((failed + 1)); \
		elif [ $$expect_failed -ne 0 ]; then \
			failed=$$((failed + 1)); \
		else \
			passed=$$((passed + 1)); \
		fi; \
		rm -f $$out $$out.frame; \
	done; \
	printf "\n"; \
	group=klib; \
	$(TEST_SUMMARY)

test-kone: $(TEST_BINS)
	@$(TEST_COLORS); \
	passed=0; failed=0; \
	printf "\n"; \
	for t in $(TEST_BINS); do \
		if ./$$t; then \
			printf "$${bld}$${grn}[ PASS ] $${dflt}%s$${rst}\n\n" "$$t"; \
			passed=$$((passed + 1)); \
		else \
			printf "$${bld}$${red}[ FAIL ] $${dflt}%s$${rst}\n\n" "$$t"; \
			failed=$$((failed + 1)); \
		fi; \
	done; \
	group=kone; \
	$(TEST_SUMMARY)

-include $(DEPS)
