# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_fs_property import validate_readbacks
from test_trace_syscalls import validate_trace_result

class Oracles(unittest.TestCase):
    def transcript(self, payload='deadbeef'):
        return ('root@linux01:/tmp# echo deadbeef > f0\n'
                'root@linux01:/tmp# echo R25AB0\nR25AB0\n'
                'root@linux01:/tmp# cat f0\n'+payload+'\n'
                'root@linux01:/tmp# echo R25AE0\nR25AE0\n')
    def test_readback(self):
        validate_readbacks(self.transcript(), [('f0','deadbeef')], 'A')
    def test_echo_is_not_evidence(self):
        for payload in ('', 'deadbeee','root@linux01:/tmp# echo deadbeef', 'deadbeef\ndeadbeef'):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validate_readbacks(self.transcript(payload), [('f0','deadbeef')], 'A')
    def test_missing_boundaries(self):
        with self.assertRaises(ValueError):
            validate_readbacks(self.transcript().replace('\nR25AB0\n','\n'), [('f0','deadbeef')], 'A')
    def test_trace_mutations(self):
        events=[{'type':'boot_start'}, {'type':'syscall','data':{'number':3}},
                {'type':'syscall','data':{'number':4}}, {'type':'shutdown','data':{'status':0}}]
        output='[bemu-linux01] RESULT: PASS after 100 KVM exits\n'
        self.assertEqual(validate_trace_result(0,output,events),2)
        for rc,out,ev in ((1,output,events),(0,'',events),(0,output,events[:2]+events[3:]),
                          (0,output,events[:-1]),(0,output+'Kernel panic: bad\n',events)):
            with self.subTest(rc=rc,out=out,ev=ev), self.assertRaises(ValueError):
                validate_trace_result(rc,out,ev)


class I386RangeModel(unittest.TestCase):
    def test_explicit_32_bit_bounds(self):
        # Independent arithmetic model; does not claim execution of i386 kernel code.
        def valid(start,size,limit,base):
            if not 0<start<=0xffffffff or not 0<=size<=0x7fffffff:return False
            if not size:return True
            if start>=limit or size>limit-start:return False
            end=start+size-1
            return start<=0xffffffff-base and end<=0xffffffff-base
        self.assertTrue(valid(0xffff,1,0x10000,0xffff0000))
        self.assertFalse(valid(0xffff,2,0x10001,0xffff0000))
        self.assertFalse(valid(0x10000,1,0x20000,0xffff0000))
        self.assertFalse(valid(0x4000000,1,0x4000000,0))
        self.assertTrue(valid(0x3ffffff,1,0x4000000,0))

if __name__=='__main__': unittest.main()
