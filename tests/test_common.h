#ifndef TEST_COMMON_H
#define TEST_COMMON_H

#include <stdio.h>
#include <unistd.h>

#define TEST_CLR_GREEN "\033[0;32m"
#define TEST_CLR_RED "\033[0;31m"
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

// gtest-style suite header/footer and per-test run markers. Tests abort via
// assert() on failure, so a crash simply cuts the log short and the Makefile
// reports the binary as FAILED -- there is no per-test FAILED line here.
#define TEST_MODULE_BEGIN(module, count)                                       \
    do {                                                                       \
        printf("Running %d tests from %s:\n", (count), (module));              \
    } while (0)

#define TEST_MODULE_END(module, count)                                         \
    do {                                                                       \
        test_tag(TEST_CLR_GREEN, "             ");                             \
        printf("%d tests from %s ran.\n", (count), (module));                  \
        test_tag(TEST_CLR_GREEN, "[  PASSED  ] ");                             \
        printf("%d tests.\n", (count));                                        \
    } while (0)

#define RUN_TEST(fn, ...)                                                      \
    do {                                                                       \
        fn(__VA_ARGS__);                                                       \
        test_tag(TEST_CLR_GREEN, "[    OK    ] ");                             \
        printf("%s\n", #fn);                                                   \
    } while (0)

#endif
