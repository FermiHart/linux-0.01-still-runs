# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
import unittest,subprocess,tempfile
from pathlib import Path
from test_contracts import ROOT
class CutCli(unittest.TestCase):
    def test_cut_options(self):
        body=r'''
#include <assert.h>
#include "cli.h"
int main(void) {
    struct cli_options o;
    char *good[]={"bemu","--root","copy.img","--power-cut-lba","0","--power-cut-phase","committed","--power-cut-copy","new.img"};
    char *bad[]={"bemu","--power-cut-lba","1","--power-cut-phase","payload"};
    char *negative[]={"bemu","--root","copy.img","--power-cut-lba","-1","--power-cut-phase","irq"};
    char *overflow[]={"bemu","--root","copy.img","--power-cut-lba","4294967296","--power-cut-phase","irq"};
    assert(!cli_parse_args(9,good,&o)); assert(o.power_cut_lba==0 && o.power_cut_phase==3);
    assert(cli_parse_args(7,good,&o)); assert(cli_parse_args(5,bad,&o)); assert(cli_parse_args(5,good,&o));
    assert(cli_parse_args(7,negative,&o)); assert(cli_parse_args(7,overflow,&o));
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'t.c').write_text(body)
            subprocess.run(['cc','-Wall','-Wextra','-Werror','-I'+str(ROOT/'bemu'),str(p/'t.c'),str(ROOT/'bemu/cli.c'),'-o',str(p/'t')],check=True,timeout=30)
            subprocess.run([str(p/'t')],check=True,timeout=10)
if __name__=='__main__':unittest.main()
