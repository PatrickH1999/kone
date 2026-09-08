# Shell snippets shared by both makefiles; TEST_SUMMARY reads the shell
# variables 'group', 'passed' and 'failed', RM_RF reads 'targets'.
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

# A FUSE mount (the author's Cryptomator vault) unlinks lazily, so a directory
# whose files were open a moment ago still reports "not empty" on the first try.
RM_RF = for dir in $$targets; do \
    n=0; \
    while [ -e "$$dir" ] && [ $$n -lt 3 ]; do \
        rm -rf "$$dir" 2> /dev/null; \
        n=$$((n + 1)); \
        [ -e "$$dir" ] && sleep 1; \
    done; \
    if [ -e "$$dir" ]; then rm -rf "$$dir" || exit 1; fi; \
done
