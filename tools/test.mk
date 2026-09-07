# Shell snippets shared by the test recipes of both makefiles;
# TEST_SUMMARY reads the shell variables 'group', 'passed' and 'failed'.
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
