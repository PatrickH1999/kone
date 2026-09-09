# The circuits. Run these from the repo root as `make logisim_<target>`, which
# forwards here; inside this directory the targets are `circ`, `test` and so
# on. The boards built from these same circuits are kicad/'s.

ROOT := ..

include $(ROOT)/tools/test.mk

SCRIPTS := $(wildcard python/build_*.py)

# What the generator writes: build_<name>.py -> <name>.circ. Hand-drawn
# circuits here are not in this list and survive `clean`.
CIRCS := $(patsubst python/build_%.py,%.circ,$(SCRIPTS))

# Logisim's own simulator, which `test` runs kone.circ in. Not a build
# dependency, which is why it is not one of the top-level test groups.
LOGISIM_JAR ?= /usr/share/java/logisim-evolution/logisim-evolution.jar

# The program baked into kone.circ's ROM, named from the repo root.
LOGISIM_PROG ?= bin/display.bin

# What the headless harness boots, mirroring the CASES table in KoneTest.java.
PROGRAMS := display hello keyboard test_klib_mem

.PHONY: alu circ clean cpu regfile test

# The kasm binaries come from the top-level makefile.
$(ROOT)/bin/%.bin:
	@$(MAKE) -C $(ROOT) bin/$*.bin

circ: $(ROOT)/$(LOGISIM_PROG)
	@for s in $(SCRIPTS); do python3 $$s || exit 1; done

alu:
	@python3 python/build_alu.py

cpu: $(ROOT)/$(LOGISIM_PROG)
	@python3 python/build_kone.py $(ROOT)/$(LOGISIM_PROG)

regfile:
	@python3 python/build_regfile.py

clean:
	rm -f $(CIRCS)
	@targets='bin python/__pycache__ python/logisim/__pycache__'; $(RM_RF)

# kone.circ booted headlessly in Logisim; needs a JDK and $(LOGISIM_JAR). The
# harness reads its programs from the repo root, so java runs from there. It
# also runs on a copy: Logisim's loader stops on a .circ.autosave beside the
# file, which it leaves there while the same file is open in its GUI.
test: circ $(PROGRAMS:%=$(ROOT)/bin/%.bin)
	@$(TEST_COLORS); \
	passed=0; failed=0; \
	printf "\n"; \
	if javac -cp $(LOGISIM_JAR) -d bin java/KoneTest.java \
		&& cp kone.circ bin/kone.circ \
		&& (cd $(ROOT) && java -Djava.awt.headless=true \
			-cp $(LOGISIM_JAR):logisim/bin KoneTest logisim/bin/kone.circ); then \
		passed=1; \
	else \
		failed=1; \
	fi; \
	printf "\n"; \
	group=logisim; \
	$(TEST_SUMMARY)
