#include "test_args.h"

#include <fcntl.h>

// getopt_long keeps its scanning state between calls; assigning 0 to optind is
// how GNU getopt is told to start over, which every case here needs.
static Args parse(char *argv[]) {
    Args args;
    optind = 0;
    int argc = 0;
    while (argv[argc] != NULL)
        argc++;
    parse_args(&args, argc, argv);
    return args;
}

// Runs parse_args in a child with its output dropped and returns the exit
// status, so the paths that end in print_usage()/print_help() can be checked
// without taking the test binary down with them.
static int parse_exit_status(char *argv[]) {
    pid_t pid = fork();
    if (pid == 0) {
        // The child inherits this process's stdio buffers and the exit() in
        // print_usage()/print_help() flushes them, so the descriptors are
        // pointed at /dev/null rather than the streams reopened: freopen()
        // would flush the report so far to the real stdout on its way out.
        const int null_fd = open("/dev/null", O_WRONLY);
        dup2(null_fd, STDOUT_FILENO);
        dup2(null_fd, STDERR_FILENO);
        parse(argv);
        _exit(0);
    }
    int status = 0;
    waitpid(pid, &status, 0);
    return WIFEXITED(status) ? WEXITSTATUS(status) : -1;
}

int main() {
    TEST_MODULE_BEGIN("args", 8);
    RUN_TEST(test_args_defaults);
    RUN_TEST(test_args_bootfile);
    RUN_TEST(test_args_clockspeed);
    RUN_TEST(test_args_log);
    RUN_TEST(test_args_verbose_stacked);
    RUN_TEST(test_args_verbose_explicit);
    RUN_TEST(test_args_verbose_clamped);
    RUN_TEST(test_args_missing_bootfile_exits);
    TEST_MODULE_END("args", 8);
    return TEST_EXIT_CODE;
}

void test_args_defaults() {
    char *argv[] = {"kone", "-b", "boot.bin", NULL};
    const Args args = parse(argv);
    assert(args.cycle_sleep == 0);
    assert(args.v == 0);
    assert(args.log == 0);
}

void test_args_bootfile() {
    char *shortf[] = {"kone", "-b", "boot.bin", NULL};
    assert(strcmp(parse(shortf).bootfile, "boot.bin") == 0);
    char *longf[] = {"kone", "--bootfile", "other.bin", NULL};
    assert(strcmp(parse(longf).bootfile, "other.bin") == 0);
}

void test_args_clockspeed() {
    char *shortf[] = {"kone", "-b", "boot.bin", "-t", "100", NULL};
    assert(parse(shortf).cycle_sleep == 100);
    char *longf[] = {"kone", "-b", "boot.bin", "--clockspeed=20000", NULL};
    assert(parse(longf).cycle_sleep == 20000);
}

void test_args_log() {
    char *argv[] = {"kone", "-b", "boot.bin", "-l", NULL};
    assert(parse(argv).log == 1);
    char *longf[] = {"kone", "-b", "boot.bin", "--log", NULL};
    assert(parse(longf).log == 1);
}

// -v raises the level by one per 'v', which getopt_long hands over as one
// option with the rest folded into optarg.
void test_args_verbose_stacked() {
    char *one[] = {"kone", "-b", "boot.bin", "-v", NULL};
    assert(parse(one).v == 1);
    char *two[] = {"kone", "-b", "boot.bin", "-vv", NULL};
    assert(parse(two).v == 2);
    char *three[] = {"kone", "-b", "boot.bin", "-vvv", NULL};
    assert(parse(three).v == 3);
    char *bare_long[] = {"kone", "-b", "boot.bin", "--verbose", NULL};
    assert(parse(bare_long).v == 1);
}

// An explicit level may be attached (-v2, --verbose=2) or separated by a
// space, which getopt_long does not attach by itself.
void test_args_verbose_explicit() {
    char *attached[] = {"kone", "-b", "boot.bin", "-v2", NULL};
    assert(parse(attached).v == 2);
    char *equals[] = {"kone", "-b", "boot.bin", "--verbose=3", NULL};
    assert(parse(equals).v == 3);
    char *spaced[] = {"kone", "-b", "boot.bin", "-v", "2", NULL};
    assert(parse(spaced).v == 2);
    char *spaced_long[] = {"kone", "-b", "boot.bin", "--verbose", "1", NULL};
    assert(parse(spaced_long).v == 1);
}

void test_args_verbose_clamped() {
    char *stacked[] = {"kone", "-b", "boot.bin", "-vvvvv", NULL};
    assert(parse(stacked).v == 3);
    char *explicit_level[] = {"kone", "-b", "boot.bin", "-v9", NULL};
    assert(parse(explicit_level).v == 3);
}

void test_args_missing_bootfile_exits() {
    char *none[] = {"kone", NULL};
    assert(parse_exit_status(none) == EXIT_FAILURE);
    char *other_only[] = {"kone", "-l", NULL};
    assert(parse_exit_status(other_only) == EXIT_FAILURE);
    char *unknown[] = {"kone", "-z", NULL};
    assert(parse_exit_status(unknown) == EXIT_FAILURE);
    char *help[] = {"kone", "-h", NULL};
    assert(parse_exit_status(help) == EXIT_SUCCESS);
}
