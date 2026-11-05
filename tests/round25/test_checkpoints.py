# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
import copy,unittest
from checkpoints import compare,validate
class Checkpoints(unittest.TestCase):
    def sample(self):
        return {'schema':'linux001.checkpoints.v1','complete':True,'identity':{
            **{k:'0'*64 for k in ('source_sha256','kernel_sha256','root_sha256','input_sha256','environment_sha256')},'scope':'same-host-selected-state-v1'},
            'checkpoints':[{'ordinal':0,'input_offset':0,'registers_sha256':'1'*64,'ram_sha256':'2'*64,'devices_sha256':'3'*64}]}
    def test_equal_and_each_divergence(self):
        a=self.sample();self.assertEqual(compare(a,a)['status'],'PASS')
        for field in ('registers_sha256','ram_sha256','devices_sha256','input_offset'):
            b=copy.deepcopy(a);b['checkpoints'][0][field]=1 if field=='input_offset' else '4'*64
            self.assertEqual(compare(a,b)['field'],field)
    def test_fail_closed(self):
        a=self.sample()
        for mutate in (lambda b:b.update(complete=False),lambda b:b['checkpoints'][0].update(ordinal=1),lambda b:b['identity'].update(root_sha256='x'),lambda b:b['checkpoints'].clear(),lambda b:b['checkpoints'][0].update(input_offset=-1)):
            b=copy.deepcopy(a);mutate(b)
            with self.assertRaises(ValueError):compare(a,b)
if __name__=='__main__':unittest.main()
