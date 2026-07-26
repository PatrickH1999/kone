#ifndef TEST_COMMON_H
#define TEST_COMMON_H

#include <stdio.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

// Dimmer than the bold, fully-saturated colors `make test` uses for its
// per-binary/aggregate lines, so those summary lines stand out more.
#define TEST_CLR_GREEN "\033[38;2;0;200;0m"
#define TEST_CLR_RED "\033[38;2;200;0;0m"
#define TEST_CLR_WHITE "\033[38;2;200;200;200m"
#define TEST_CLR_RESET "\033[0m"

// Prints `tag` in `color` if stdout is a terminal, plain otherwise (so
// piped/redirected logs, e.g. `make test > log.txt`, stay free of escape
// codes).
static inline void test_tag(const char *color, const char *tag) {
    if (isatty(fileno(stdout)))
        printf("%s%s%s", color, tag, TEST_CLR_RESET);
    else
        printf("%s", tag);
}

static int test_g_failed = 0;

#define TEST_MODULE_BEGIN(module, count)                                       \
    do {                                                                       \
        (void)(module);                                                        \
        (void)(count);                                                         \
        test_g_failed = 0;                                                     \
    } while (0)

// Runs `fn` in a forked child so that a failed assert() -- which already
// prints "file:line: ... assertion failed" to stderr before calling abort()
// -- only tears down that one test. The parent reports the outcome as a
// single [ PASS ] / [ FAIL ] line and keeps going, so the remaining tests in
// this binary still run.
#define RUN_TEST(fn, ...)                                                      \
    do {                                                                       \
        pid_t _test_pid = fork();                                              \
        if (_test_pid == 0) {                                                  \
            fn(__VA_ARGS__);                                                   \
            _exit(0);                                                          \
        }                                                                      \
        int _test_status = 0;                                                  \
        waitpid(_test_pid, &_test_status, 0);                                  \
        if (WIFEXITED(_test_status) && WEXITSTATUS(_test_status) == 0) {       \
            test_tag(TEST_CLR_GREEN, "[ PASS ] ");                             \
            test_tag(TEST_CLR_WHITE, #fn);                                     \
            printf("\n");                                                      \
        } else {                                                               \
            test_tag(TEST_CLR_RED, "[ FAIL ] ");                               \
            test_tag(TEST_CLR_WHITE, #fn);                                     \
            printf("\n");                                                      \
            test_g_failed++;                                                   \
        }                                                                      \
    } while (0)

// No output here: `make test` already prints one [ PASSED ]/[ FAILED ] line
// per binary, and the per-test [ PASS ]/[ FAIL ] lines above already show
// which (if any) failed -- a module-level tally would just repeat the same
// information in a different shape.
#define TEST_MODULE_END(module, count)                                         \
    do {                                                                       \
        (void)(module);                                                        \
        (void)(count);                                                         \
    } while (0)

// Exit code for main() to return: nonzero if any test in this binary failed,
// so `make test` (which checks each binary's exit status) still reports it.
#define TEST_EXIT_CODE (test_g_failed > 0 ? 1 : 0)

#endif
