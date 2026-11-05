#!/usr/bin/env python3
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Retain paired freestanding i386 compilation and bounded host ablations.
No result from this script is guest runtime evidence.
"""
import hashlib,itertools,json,os,platform,subprocess,sys,tempfile,unittest,io
from pathlib import Path
import test_contracts as contracts
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from history_inputs import History
OUT=ROOT/'build/round25/compiler'
BASE='e6076cb47fd27e1f6ce1b831852a1efe11de99c0'
FLAGS=['-m32','-march=i386','-ffreestanding','-nostdinc','-fno-pie','-fno-pic',
       '-fno-stack-protector','-fno-asynchronous-unwind-tables','-fno-builtin',
       '-fno-strict-aliasing','-fleading-underscore','-fno-omit-frame-pointer',
       '-mpreferred-stack-boundary=2','-Wall','-Werror','-std=gnu89','-I'+str(ROOT/'include')]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    history=History(ROOT)
    cc=os.environ.get('CC','gcc')
    report={'schema':'linux001.compiler.v1','base':BASE,'compiler':subprocess.check_output([cc,'--version'],text=True).splitlines()[0],
            'host':platform.platform(),'layer':'freestanding-i386-compile-only','guest_runtime':'NOT_RUN: compile-only matrix','cells':[],'ablation':[]}
    baseline_include=OUT/'baseline-include'
    for path in history.entries(BASE,prefix='include/'):
        target=baseline_include/Path(path).relative_to('include');target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(history.file(BASE,path))
    cases=['fs/bitmap.c','fs/buffer.c','kernel/vsprintf.c','fs/fcntl.c','fs/pipe.c','fs/read_write.c','kernel/fork.c','mm/memory.c']
    for variant in ('baseline','treatment'):
        for case,opt in itertools.product(cases,('O0','O1','O2','Os')):
            prefix=OUT/(variant+'-'+case.replace('/','-')+'-'+opt)
            source=prefix.with_suffix('.c')
            source.write_bytes(history.file(BASE,case) if variant=='baseline' else (ROOT/case).read_bytes())
            obj=Path(str(prefix)+'.o');asm=Path(str(prefix)+'.s')
            flags=[x for x in FLAGS if not x.startswith('-I')]
            include=baseline_include if variant=='baseline' else ROOT/'include'
            argv=[cc,*flags,'-I'+str(include),'-'+opt,'-c',str(source),'-o',str(obj)]
            result=subprocess.run(argv,capture_output=True,text=True,timeout=30)
            log=Path(str(prefix)+'.txt');log.write_text(result.stdout+result.stderr)
            cell={'variant':variant,'source':case,'optimization':opt,'argv':argv,'status':'PASS' if result.returncode==0 else 'FAIL',
                  'source_sha256':sha(source),'returncode':result.returncode,'log':str(log.relative_to(ROOT))}
            if not result.returncode:
                cell['object_sha256']=sha(obj)
                dis=subprocess.run(['objdump','-dr',str(obj)],capture_output=True,text=True,check=True,timeout=10)
                asm.write_text(dis.stdout);cell['assembly_sha256']=sha(asm)
            report['cells'].append(cell)
    groups=[('crt0','userland/crt0.S','test_crt0_return_uses_register_argument'),
            ('dup2','fs/fcntl.c','test_dup2_preserves_source_and_validates_before_close'),
            ('bitmap','fs/bitmap.c','test_bitmap_memory_register_and_flag_contracts')]
    for bits in itertools.product((False,True),repeat=3):
        with tempfile.TemporaryDirectory(prefix='linux001-ablation-') as directory:
            fixture=Path(directory)
            for enabled,(_,path,_) in zip(bits,groups):
                target=fixture/path;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes((ROOT/path).read_bytes() if enabled else history.file(BASE,path))
            previous=contracts.ROOT;contracts.ROOT=fixture
            stream=io.StringIO()
            try:
                suite=unittest.TestSuite(contracts.Contracts(name) for _,_,name in groups)
                result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
            finally:contracts.ROOT=previous
            name=''.join('1' if x else '0' for x in bits)
            (OUT/('ablation-'+name+'.txt')).write_text(stream.getvalue())
            report['ablation'].append({'enabled':[g[0] for x,g in zip(bits,groups) if x],
              'layer':'host-production-body-and-i386-disassembly','status':'PASS' if result.wasSuccessful() else 'FAIL',
              'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'log':'build/round25/compiler/ablation-'+name+'.txt'})
    (OUT/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'compile_cells':len(report['cells']),'compile_pass':sum(c['status']=='PASS' for c in report['cells']),
       'ablation_cells':len(report['ablation']),'ablation_pass':sum(c['status']=='PASS' for c in report['ablation']),
       'guest_runtime':report['guest_runtime']}))
    return int(any(c['status']=='FAIL' and c['variant']=='treatment' for c in report['cells']))
if __name__=='__main__':sys.exit(main())
