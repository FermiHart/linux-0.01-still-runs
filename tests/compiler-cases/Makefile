# Compiler investigation harness for -O2 sensitive patterns
# in Linux 0.01 porting layer.
#
# Each case is built at -O0, -O1 and -O2, and also for the i386 ABI (-m32)
# because the original kernel targets i386.  The harness records:
#   * exit code / output of the test program
#   * disassembly of the function under investigation
#   * compiler version and command line
#
# Override CC from the top-level Makefile:
#   make -C tests/compiler-cases CC=gcc-14

CC := gcc
BASE_FLAGS := -Wall -Wextra -Werror -std=gnu89

CASES := buffer_freelist bitmap_inline_asm vsprintf_percent_s
OPT_LEVELS := O0 O1 O2
ABIS := x86_64 i386

BINS := $(foreach a,$(ABIS),$(foreach c,$(CASES),$(foreach o,$(OPT_LEVELS),build/$(c)-$(a)-$(o))))
ASMS := $(foreach a,$(ABIS),$(foreach c,$(CASES),$(foreach o,$(OPT_LEVELS),build/$(c)-$(a)-$(o).s)))

.PHONY: all clean run report

all: $(BINS) $(ASMS)

run: all
	@./run.sh

report: run
	@cat build/report.txt

compare-assembly: all
	@bash compare_asm.sh x86_64
	@bash compare_asm.sh i386

audit: all
	@bash audit.sh

summarize: all
	@python3 summarize.py

build:
	@mkdir -p build

# Convenience macro: ABI -> extra flags.
ABI_FLAGS_x86_64 :=
ABI_FLAGS_i386 := -m32 -no-pie

# Generate per-case/per-abi/per-opt binary rules.
define BIN_RULE
build/$(1)-$(2)-$(3): $(1).c | build
	$$(CC) $$(BASE_FLAGS) $$(ABI_FLAGS_$(2)) -$(3) -o $$@ $$<
endef
$(foreach c,$(CASES),$(foreach a,$(ABIS),$(foreach o,$(OPT_LEVELS),$(eval $(call BIN_RULE,$(c),$(a),$(o))))))

# Generate per-case/per-abi/per-opt assembly rules.
define ASM_RULE
build/$(1)-$(2)-$(3).s: $(1).c | build
	$$(CC) $$(BASE_FLAGS) $$(ABI_FLAGS_$(2)) -$(3) -S -fverbose-asm -o $$@ $$<
endef
$(foreach c,$(CASES),$(foreach a,$(ABIS),$(foreach o,$(OPT_LEVELS),$(eval $(call ASM_RULE,$(c),$(a),$(o))))))

clean:
	rm -rf build
