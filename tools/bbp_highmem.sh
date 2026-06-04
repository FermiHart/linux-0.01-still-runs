#!/bin/sh
# bbp_highmem.sh — print the active HIGH_MEMORY value from include/linux/config.h
# without parentheses, for the BBP build (-DBBP_L01_HIGH_MEMORY=...).
#
# config.h guards HIGH_MEMORY behind LINUS_HD / LASU_HD #ifdefs. The C
# preprocessor is the authority on which one is active, so we ask cpp directly
# instead of grepping (which would pick up the inactive branch too).
#
# F E R M I ∞ H A R T <contact@fermihart.com>  SPDX-License-Identifier: Unlicense
set -e
cc -Iinclude -E -P - <<'EOF' 2>/dev/null | awk 'NF{gsub(/[()]/,"");print $0}' | tail -1
#include <linux/config.h>
HIGH_MEMORY
EOF
