#!/usr/bin/env python3
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Typed file-based seam for jash; no jash connection/source is assumed.

Commands are selected here, never accepted as executable strings in a spec.
Normal and crash runs use isolated image copies. All writes stay in the chosen
output directory or the intentionally disposable guest Minix namespace.
"""
import argparse,hashlib,json,os,platform,re,shutil,subprocess,sys,time
from pathlib import Path
from minix_model import MinixModel,ModelError
from minix_reader import MinixImage,ImageError
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests'))
from harness_utils import BEMU_PASS_RE,KERNEL_FAULT_RE,sanitize_terminal
OPS={'create','write','append','link','unlink','mkdir','rmdir'}
PATH=re.compile(r'/tmp/r25(?:/[A-Za-z0-9_]{1,14}){1,3}\Z')
DATA=re.compile(r'[A-Za-z0-9_]{0,64}\Z')
PHASES={'accepted','payload','committed','irq'}

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def validate(spec):
    if not isinstance(spec,dict) or set(spec)-{'schema','id','kind','seed','timeout_seconds','max_exits','operations','cut'}:raise ValueError('unknown experiment fields')
    if spec.get('schema')!='linux001.experiment.v1':raise ValueError('schema')
    if not isinstance(spec.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',spec['id']):raise ValueError('id')
    if spec.get('kind') not in ('filesystem','crash_cut'):raise ValueError('kind')
    for key,lower,upper in (('seed',0,2**32-1),('timeout_seconds',1,300),('max_exits',1,50000000)):
        if type(spec.get(key)) is not int or not lower<=spec[key]<=upper:raise ValueError(key)
    ops=spec.get('operations')
    if not isinstance(ops,list) or not 1<=len(ops)<=32:raise ValueError('operations bounds')
    for op in ops:
        if not isinstance(op,dict) or not isinstance(op.get('op'),str) or op['op'] not in OPS:raise ValueError('operation')
        expected={'op','path'}|({'data'} if op['op'] in ('write','append') else {'target'} if op['op']=='link' else set())
        if set(op)!=expected:raise ValueError('operation fields')
        if not isinstance(op['path'],str) or not PATH.fullmatch(op['path']):raise ValueError('operation path')
        if 'target' in op and (not isinstance(op['target'],str) or not PATH.fullmatch(op['target'])):raise ValueError('link target')
        if 'data' in op and (not isinstance(op['data'],str) or not DATA.fullmatch(op['data'])):raise ValueError('payload')
    cut=spec.get('cut')
    if spec['kind']=='crash_cut':
        if not isinstance(cut,dict) or set(cut)!={'lba','phase'} or type(cut['lba']) is not int or not 0<=cut['lba']<=2**32-1 or not isinstance(cut['phase'],str) or cut['phase'] not in PHASES:raise ValueError('cut')
    elif cut is not None:raise ValueError('cut on ordinary run')
    render(spec) # reject invalid model transitions before touching images
    return spec

def render(spec):
    model=MinixModel(inodes=128,blocks=1024,fds=20)
    model.apply({'op':'mkdir','path':'/tmp'});model.apply({'op':'mkdir','path':'/tmp/r25'})
    commands=['mkdir /tmp/r25'];touched=set()
    for original in spec['operations']:
        op=dict(original);kind=op['op'];path=op['path'];touched.add(path)
        if kind in ('write','append'):
            commands.append(f"echo {op['data']} {'>>' if kind=='append' else '>'} {path}")
            op['data']+='\n' # the existing shell echo always writes a newline
        elif kind=='link':commands.append(f"ln {path} {op['target']}");touched.add(op['target'])
        else:commands.append({'create':'touch','unlink':'rm','mkdir':'mkdir','rmdir':'rmdir'}[kind]+' '+path)
        try:model.apply(op)
        except ModelError as e:raise ValueError('invalid planned transition: '+str(e)) from None
    commands+=['sync','halt']
    return '\n'.join(commands)+'\n',model,touched

def inspect(image,model,touched):
    del touched # compare the entire isolated namespace, including unexpected entries
    reader=MinixImage(image)
    expected={p for p in model.paths if p=='/tmp/r25' or p.startswith('/tmp/r25/')}
    actual={};directories=set()
    def walk(path,ino,parent):
        if len(actual)>=128:raise ValueError('namespace inspection bound')
        actual[path]=ino;node=reader.inode(ino)
        if node['mode']&0xf000==0x4000:
            if ino in directories:raise ValueError('directory cycle/alias')
            directories.add(ino);entries=reader.directory(ino)
            if entries.get('.')!=ino or entries.get('..')!=parent:raise ValueError('directory parent identity')
            for name,child in entries.items():
                if name in ('.','..'):continue
                if '/' in name or not name:raise ValueError('invalid directory name')
                walk(path+'/'+name,child,ino)
    walk('/tmp/r25',reader.resolve('/tmp/r25'),reader.resolve('/tmp'))
    if set(actual)!=expected:raise ValueError('namespace path set mismatch')
    forward={};reverse={}
    for path in sorted(expected):
        ino=actual[path];wanted=model.node(path);found=reader.inode(ino);key=model.paths[path]
        if found['mode']&0xf000!=(0x4000 if wanted.kind=='dir' else 0x8000):raise ValueError('inode kind mismatch: '+path)
        if wanted.kind=='file':
            if reader.data(ino)!=wanted.data:raise ValueError('payload mismatch: '+path)
            if found['links']!=wanted.names:raise ValueError('link count mismatch: '+path)
        if key in forward and forward[key]!=ino:raise ValueError('hard-link identity mismatch')
        if ino in reverse and reverse[ino]!=key:raise ValueError('independent files alias unexpectedly')
        forward[key]=ino;reverse[ino]=key


def run(spec,output,kernel,root,bemu):
    validate(spec);output=Path(output);output.mkdir(parents=True,exist_ok=False)
    (output/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    script,model,touched=render(spec);(output/'input.txt').write_text(script)
    report={'schema':'linux001.result.v1','id':spec['id'],'seed':spec['seed'],'status':'INFRA_ERROR',
            'layer':'linux001-guest','jash_connected':False,'environment':platform.platform(),
            'input_sha256':hashlib.sha256(script.encode()).hexdigest(),'scope':'exact orderly payload/namespace checks' if spec['kind']=='filesystem' else 'requested IDE cut reached; no recovery claim'}
    try:
        if not Path('/dev/kvm').exists():
            report.update(status='BLOCKED',reason='/dev/kvm is absent');return report
        for path in (kernel,root,bemu):
            if not Path(path).is_file():raise ValueError('missing artifact: '+str(path))
        before=digest(root);report.update(kernel_sha256=digest(kernel),root_source_sha256=before,runner_sha256=digest(bemu))
        reader=MinixImage(root)
        try:reader.resolve('/tmp/r25')
        except ImageError as e:
            if not str(e).startswith('path not found:'):raise
        else:raise ValueError('source already contains /tmp/r25; refuse ambiguous initial state')
        image=output/'root.img';trace=output/'trace.jsonl'
        argv=[str(Path(bemu).resolve()),'--kernel',str(Path(kernel).resolve()),'--keys',script,
              '--max-exits',str(spec['max_exits']),'--trace-file',str(trace.resolve())]
        if spec['kind']=='crash_cut':
            cut=spec['cut'];argv+=['--root',str(Path(root).resolve()),'--power-cut-lba',str(cut['lba']),
              '--power-cut-phase',cut['phase'],'--power-cut-copy',str(image.resolve())]
        else:shutil.copyfile(root,image);argv+=['--root',str(image.resolve())]
        report['argv']=argv;started=time.monotonic()
        try:process=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=spec['timeout_seconds'])
        except subprocess.TimeoutExpired as e:
            (output/'console.txt').write_bytes(e.stdout or b'');report.update(status='TIMEOUT',reason='bounded guest timeout');return report
        report.update(returncode=process.returncode,wall_seconds=time.monotonic()-started)
        (output/'console.txt').write_bytes(process.stdout);text=sanitize_terminal(process.stdout)
        if digest(root)!=before:raise ValueError('canonical source changed')
        report['root_result_sha256']=digest(image)
        if spec['kind']=='crash_cut':
            wanted=f"POWER_CUT lba={spec['cut']['lba']} phase={['accepted','payload','committed','irq'].index(spec['cut']['phase'])+1}"
            report.update(status='PASS' if process.returncode==3 and wanted in text else 'FAIL')
            try:inspect(image,model,touched);report['post_cut_semantics']='matches final plan'
            except (ValueError,ImageError) as e:report['post_cut_semantics']='differs: '+str(e)
        elif process.returncode or not BEMU_PASS_RE.search(text) or KERNEL_FAULT_RE.search(text) or not re.search(r'(?m)^System halted\.$',text) or not re.search(r'(?m)^\[bemu-linux01\] guest halted with interrupts disabled after power request$',text):
            report.update(status='FAIL',reason='runner/guest termination oracle')
        else:
            try:inspect(image,model,touched);report.update(status='PASS')
            except (ValueError,ImageError) as e:report.update(status='FAIL',reason=str(e))
        return report
    except (OSError,ValueError,subprocess.SubprocessError) as e:
        report.update(status='INFRA_ERROR',reason=str(e));return report
    finally:
        (output/'result.json').write_text(json.dumps(report,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('spec');p.add_argument('--output',required=True)
    p.add_argument('--kernel',default='build/kernel.bin');p.add_argument('--root',default='build/root.img');p.add_argument('--bemu',default='build/bemu-linux01')
    a=p.parse_args();spec=json.loads(Path(a.spec).read_text());report=run(spec,a.output,a.kernel,a.root,a.bemu)
    print(json.dumps(report));return 0 if report['status']=='PASS' else 77 if report['status']=='BLOCKED' else 1
if __name__=='__main__':sys.exit(main())
