# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
import os,subprocess,tempfile,unittest
from pathlib import Path
from test_contracts import ROOT
class CrashCopy(unittest.TestCase):
    def test_source_unchanged_existing_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            d=Path(directory);source=d/'source';source.write_bytes(bytes(range(256))*1000)
            code=d/'t.c';binary=d/'t'
            code.write_text('#include "'+str(ROOT/'bemu/crash_copy.h')+'"\nint main(int c,char **v) { if(c!=3)return 2;return copy_crash_image(v[1],v[2])?1:0;}\n')
            subprocess.run(['cc','-Wall','-Wextra','-Werror',str(code),'-o',str(binary)],check=True,timeout=30)
            before=source.read_bytes();dest=d/'copy'
            self.assertEqual(subprocess.run([str(binary),str(source),str(dest)],timeout=10).returncode,0)
            self.assertEqual(dest.read_bytes(),before)
            self.assertEqual(subprocess.run([str(binary),str(source),str(dest)],timeout=10).returncode,1)
            link=d/'link';link.symlink_to(source)
            self.assertEqual(subprocess.run([str(binary),str(source),str(link)],timeout=10).returncode,1)
            self.assertEqual(source.read_bytes(),before)
if __name__=='__main__':unittest.main()
