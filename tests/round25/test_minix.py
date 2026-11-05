# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
import json,struct,tempfile,unittest
from pathlib import Path
from minix_model import MinixModel,ModelError,generate,execute,shrink
from minix_reader import MinixImage,ImageError

class ModelTests(unittest.TestCase):
    def test_seeded_state_and_replay(self):
        for seed in range(64):
            ops=generate(seed,200);a,ra=execute(ops);b,rb=execute(generate(seed,200))
            self.assertEqual(a.manifest(),b.manifest());self.assertEqual(ra,rb)
    def test_hardlink_unlink_open_lifetime(self):
        m=MinixModel();m.apply({'op':'create','path':'/f'})
        m.apply({'op':'write','path':'/f','data':'proof'})
        fd=m.apply({'op':'open','path':'/f'})
        m.apply({'op':'link','path':'/f','target':'/g'});m.apply({'op':'unlink','path':'/f'})
        self.assertEqual(m.apply({'op':'read','path':'/g'}),b'proof')
        m.apply({'op':'unlink','path':'/g'});self.assertEqual(len(m.nodes),2)
        m.apply({'op':'close','fd':fd});self.assertEqual(len(m.nodes),1)
    def test_exhaustion_and_recovery(self):
        m=MinixModel(inodes=2,blocks=2,fds=2);m.apply({'op':'create','path':'/f'})
        with self.assertRaisesRegex(ModelError,'ENOSPC'):m.apply({'op':'create','path':'/g'})
        m.apply({'op':'write','path':'/f','data':'x'*1024})
        with self.assertRaisesRegex(ModelError,'ENOSPC'):m.apply({'op':'append','path':'/f','data':'y'})
        self.assertEqual(len(m.node('/f').data),1024)
        m.apply({'op':'open','path':'/f'});m.apply({'op':'open','path':'/f'})
        with self.assertRaisesRegex(ModelError,'EMFILE'):m.apply({'op':'open','path':'/f'})
        m.apply({'op':'close','fd':0});self.assertEqual(m.apply({'op':'open','path':'/f'}),0)
        m.apply({'op':'truncate','path':'/f'});self.assertEqual(m.used_blocks(),1)
    def test_indirect_accounting(self):
        m=MinixModel(blocks=1024);m.apply({'op':'create','path':'/f'})
        for n,blocks in ((7,7),(8,9),(519,520),(520,523)):
            m.node('/f').data=b'x'*(n*1024);self.assertEqual(m.blocks(m.node('/f')),blocks)
    def test_reducer(self):
        seq=[{'op':'mkdir','path':'/d'},{'op':'create','path':'/f'},
             {'op':'write','path':'/f','data':'BAD'},{'op':'read','path':'/f'}]
        def fails(ops):return any(x.get('data_hex')=='424144' for x in execute(ops)[0].manifest().values())
        reduced=shrink(seq,fails)
        self.assertEqual([x['op'] for x in reduced],['create','write'])
        for i in range(len(reduced)):self.assertFalse(fails(reduced[:i]+reduced[i+1:]))
    def test_inode_reuse_and_directory_high_water(self):
        m=MinixModel(inodes=128,blocks=128)
        for _ in range(200):
            m.apply({'op':'create','path':'/f'});self.assertEqual(m.paths['/f'],2)
            m.apply({'op':'unlink','path':'/f'})
        for i in range(63):m.apply({'op':'create','path':'/f'+str(i)})
        self.assertEqual(m.blocks(m.nodes[1]),2)
        for i in range(63):m.apply({'op':'unlink','path':'/f'+str(i)})
        self.assertEqual(m.blocks(m.nodes[1]),2) # retained directory holes
        m.apply({'op':'create','path':'/again'});self.assertEqual(m.blocks(m.nodes[1]),2)

    def test_name_and_directory_bounds(self):
        m=MinixModel();m.apply({'op':'create','path':'/'+'a'*14})
        with self.assertRaises(ModelError):m.apply({'op':'create','path':'/'+'a'*15})
        m.apply({'op':'mkdir','path':'/d'});m.apply({'op':'create','path':'/d/f'})
        with self.assertRaisesRegex(ModelError,'ENOTEMPTY'):m.apply({'op':'rmdir','path':'/d'})

class ReaderTests(unittest.TestCase):
    def fixture(self,d):
        fs=bytearray(32*1024);struct.pack_into('<6HIH',fs,1024,16,32,1,1,5,0,0x7fffffff,0x137f)
        # independent explicit two-inode fixture, no image-builder code reused
        struct.pack_into('<HHIIBB9H',fs,4096,0x41ed,0,48,0,0,2,5,0,0,0,0,0,0,0,0)
        struct.pack_into('<HHIIBB9H',fs,4128,0x81a4,0,5,0,0,1,6,0,0,0,0,0,0,0,0)
        for i,(ino,name) in enumerate(((1,b'.'),(1,b'..'),(2,b'proof'))):struct.pack_into('<H14s',fs,5120+i*16,ino,name)
        fs[6144:6149]=b'proof';mbr=bytearray(512);mbr[510:512]=b'\x55\xaa';struct.pack_into('<II',mbr,454,1,64)
        p=Path(d)/'fixture.img';p.write_bytes(mbr+fs);return p
    def test_exact_payload_and_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.fixture(d);self.assertEqual(MinixImage(p).read('/proof'),b'proof')
            raw=bytearray(p.read_bytes());raw[512+6144]^=1;p.write_bytes(raw)
            self.assertNotEqual(MinixImage(p).read('/proof'),b'proof')
    def test_bad_zone_and_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.fixture(d);raw=bytearray(p.read_bytes());struct.pack_into('<H',raw,512+4128+14,32);p.write_bytes(raw)
            with self.assertRaises(ImageError):MinixImage(p).read('/proof')
            p.write_bytes(raw[:-1])
            with self.assertRaises(ImageError):MinixImage(p)
if __name__=='__main__':unittest.main()
