# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
import copy,json,tempfile,unittest
from pathlib import Path
from experiment import validate,render,ROOT
class Experiment(unittest.TestCase):
    def sample(self):return json.loads((ROOT/'tests/round25/example-experiment.json').read_text())
    def test_schema_and_render(self):
        s=self.sample();validate(s);script,model,touched=render(s)
        self.assertTrue(script.endswith('sync\nhalt\n'))
        self.assertEqual(model.node('/tmp/r25/alias').data,b'R25_PAYLOAD\n')
        self.assertNotIn('/tmp/r25/proof',model.paths)
    def test_reject_unbounded_untyped_and_shell_payloads(self):
        for mutate in (lambda s:s.update(seed=True),lambda s:s.update(timeout_seconds=301),
                       lambda s:s.update(argv=['rm','-rf','/']),lambda s:s['operations'][0].update(path='/etc/passwd'),
                       lambda s:s['operations'][1].update(data='x;halt'),lambda s:s['operations'][0].update(extra=1),
                       lambda s:s.update(operations=[])):
            s=self.sample();mutate(s)
            with self.assertRaises(ValueError):validate(s)

class InspectionOracle(unittest.TestCase):
    def test_namespace_and_alias_mutations(self):
        from unittest.mock import patch
        from experiment import inspect
        from minix_model import MinixModel
        m=MinixModel()
        for path in ('/tmp','/tmp/r25'):m.apply({'op':'mkdir','path':path})
        for path in ('/tmp/r25/a','/tmp/r25/b'):
            m.apply({'op':'create','path':path});m.apply({'op':'write','path':path,'data':'same'})
        class Reader:
            entries={'.':3,'..':2,'a':4,'b':5}
            def resolve(self,path):return {'/tmp':2,'/tmp/r25':3}[path]
            def inode(self,n):return {'mode':0x41ed if n==3 else 0x81a4,'links':1}
            def directory(self,n):return self.entries
            def data(self,n):return b'same'
        r=Reader()
        with patch('experiment.MinixImage',return_value=r):
            inspect('unused',m,set())
            r.entries={'.':3,'..':2,'a':4,'b':5,'extra':6}
            with self.assertRaisesRegex(ValueError,'path set'):inspect('unused',m,set())
            r.entries={'.':3,'..':2,'a':4,'b':4}
            with self.assertRaisesRegex(ValueError,'alias'):inspect('unused',m,set())

if __name__=='__main__':unittest.main()
