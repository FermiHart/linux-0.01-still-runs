# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
import unittest
from test_contracts import c_run,ROOT

class GuestAddress(unittest.TestCase):
    def test_segmented_paged_fetch_and_boundaries(self):
        c_run(r'''
#include <assert.h>
#include <string.h>
#include "'''+str(ROOT/'bemu/guest_address.h')+r'''"
static int mapping(void *context, uint32_t linear, uint64_t *physical) {
    (void)context;
    if (linear==0x4000fff) { *physical=7; return 0; }
    if (linear==0x4001000) { *physical=19; return 0; }
    if (linear==0x5000000) { *physical=32; return 0; }
    return -1;
}
int main(void) {
    unsigned char ram[32]={0}, out[2]; ram[7]=0xcd; ram[19]=0x80;
    assert(!guest_fetch32(ram,32,0x4000000,0xffff,0xfff,out,2,mapping,0));
    assert(out[0]==0xcd && out[1]==0x80);
    assert(guest_fetch32(ram,32,0,0xffff,0xfff,out,2,mapping,0));
    assert(guest_fetch32(ram,32,0x4000000,0xfff,0xfff,out,2,mapping,0));
    assert(guest_fetch32(ram,32,0xffffffff,0xffff,1,out,2,mapping,0));
    assert(guest_fetch32(ram,32,0x5000000,0xffff,0,out,1,mapping,0));
    assert(guest_fetch32(ram,32,0,0xffffffff,0x100000000ULL,out,2,mapping,0));
    return 0;
}
''',sanitize=True)

if __name__=='__main__': unittest.main()
