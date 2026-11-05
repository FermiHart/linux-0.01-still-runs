# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Bounded abstract Minix namespace/resource oracle, not kernel execution.

Operations are atomic on ENOSPC in this model. Linux partial-write behavior must
be measured separately; do not interpret this model as a crash-consistency spec.
"""
from dataclasses import dataclass
import random

class ModelError(Exception): pass

@dataclass
class Inode:
    kind:str
    data:bytes=b''
    names:int=1
    opens:int=0
    directory_slots:int=2

class MinixModel:
    def __init__(self,inodes=16,blocks=64,fds=8):
        self.inode_limit,self.block_limit,self.fd_limit=inodes,blocks,fds
        self.paths={'/':1};self.nodes={1:Inode('dir')};self.fds={}
    def name(self,path):
        if not isinstance(path,str) or not path.startswith('/') or path=='/' or path.endswith('/'):
            raise ModelError('EINVAL')
        parts=path[1:].split('/')
        if any(p in ('','.','..') or len(p.encode())>14 for p in parts):raise ModelError('ENAMETOOLONG')
        parent=path.rsplit('/',1)[0] or '/'
        if parent not in self.paths or self.nodes[self.paths[parent]].kind!='dir':raise ModelError('ENOENT')
    def node(self,path):
        if path not in self.paths:raise ModelError('ENOENT')
        return self.nodes[self.paths[path]]
    def blocks(self,node):
        if node.kind=='dir':return (node.directory_slots*16+1023)//1024
        n=(len(node.data)+1023)//1024
        return n+int(n>7)+(1+(n-7-512+511)//512 if n>7+512 else 0)
    def used_blocks(self):return sum(self.blocks(n) for n in self.nodes.values())
    def _collect(self,ino):
        if self.nodes[ino].names==0 and self.nodes[ino].opens==0:del self.nodes[ino]
    def apply(self,op):
        kind=op['op'];path=op.get('path','')
        if kind in ('create','mkdir'):
            self.name(path)
            if path in self.paths:raise ModelError('EEXIST')
            if len(self.nodes)>=self.inode_limit:raise ModelError('ENOSPC')
            ino=next(i for i in range(1,self.inode_limit+1) if i not in self.nodes)
            parent=self.node(path.rsplit('/',1)[0] or '/');old_slots=parent.directory_slots
            self.nodes[ino]=Inode('dir' if kind=='mkdir' else 'file');self.paths[path]=ino
            parent.directory_slots=max(old_slots,2+sum(p!='/' and (p.rsplit('/',1)[0] or '/')==(path.rsplit('/',1)[0] or '/') for p in self.paths))
            if self.used_blocks()>self.block_limit:
                del self.paths[path];del self.nodes[ino];parent.directory_slots=old_slots;raise ModelError('ENOSPC')
        elif kind in ('write','append','truncate'):
            node=self.node(path)
            if node.kind!='file':raise ModelError('EISDIR')
            old=node.data;payload=op.get('data','').encode()
            node.data=(old+payload if kind=='append' else payload if kind=='write' else b'')
            if self.used_blocks()>self.block_limit:node.data=old;raise ModelError('ENOSPC')
        elif kind=='link':
            self.name(op['target']);node=self.node(path)
            if node.kind!='file':raise ModelError('EPERM')
            if op['target'] in self.paths:raise ModelError('EEXIST')
            if node.names>=255:raise ModelError('EMLINK')
            target_parent=op['target'].rsplit('/',1)[0] or '/'
            parent=self.node(target_parent);old_slots=parent.directory_slots
            self.paths[op['target']]=self.paths[path];node.names+=1
            parent.directory_slots=max(old_slots,2+sum(p!='/' and (p.rsplit('/',1)[0] or '/')==target_parent for p in self.paths))
            if self.used_blocks()>self.block_limit:
                del self.paths[op['target']];node.names-=1;parent.directory_slots=old_slots;raise ModelError('ENOSPC')
        elif kind in ('unlink','rmdir'):
            node=self.node(path)
            if path=='/':raise ModelError('EBUSY')
            if (node.kind=='dir') != (kind=='rmdir'):raise ModelError('EINVAL')
            if node.kind=='dir' and any(p.startswith(path+'/') for p in self.paths):raise ModelError('ENOTEMPTY')
            ino=self.paths.pop(path);node.names-=1;self._collect(ino)
        elif kind=='open':
            node=self.node(path)
            if node.kind!='file':raise ModelError('EISDIR')
            free=next((f for f in range(self.fd_limit) if f not in self.fds),None)
            if free is None:raise ModelError('EMFILE')
            self.fds[free]=self.paths[path];node.opens+=1;return free
        elif kind=='close':
            fd=op['fd']
            if fd not in self.fds:raise ModelError('EBADF')
            ino=self.fds.pop(fd);self.nodes[ino].opens-=1;self._collect(ino)
        elif kind=='read':return self.node(path).data
        else:raise ModelError('EINVAL')
        self.check()
    def check(self):
        assert all(1<=i<=self.inode_limit for i in self.nodes)
        assert len(self.nodes)<=self.inode_limit and self.used_blocks()<=self.block_limit
        assert len(self.fds)<=self.fd_limit
        for i,n in self.nodes.items():
            assert n.names==sum(v==i for v in self.paths.values())
            assert n.opens==sum(v==i for v in self.fds.values())
            assert n.names or n.opens
        assert all(i in self.nodes for i in self.paths.values())
    def manifest(self):
        return {p:{'inode':i,'kind':self.nodes[i].kind,'data_hex':self.nodes[i].data.hex(),
                   'namespace_references':self.nodes[i].names} for p,i in sorted(self.paths.items())}

def generate(seed,count=100):
    if count<0 or count>10000:raise ValueError('bounded to 10000 operations')
    r=random.Random(seed);ops=[]
    for _ in range(count):
        kind=r.choice(('create','write','append','truncate','link','unlink','mkdir','rmdir','open','close','read'))
        path='/'+r.choice(('f','d'))+str(r.randrange(8))
        op={'op':kind,'path':path}
        if kind in ('write','append'):op['data']=f'{r.getrandbits(64):016x}'
        if kind=='link':op['target']='/f'+str(r.randrange(8))
        if kind=='close':op['fd']=r.randrange(8)
        ops.append(op)
    return ops

def execute(ops,model=None):
    model=model or MinixModel();results=[]
    for op in ops:
        try:results.append(('OK',model.apply(op)))
        except ModelError as e:results.append((str(e),None))
        model.check()
    return model,results

def shrink(sequence,fails):
    """Deletion-minimal under a deterministic predicate, not globally shortest."""
    result=list(sequence)
    if not fails(result):raise ValueError('input is not a failing sequence')
    width=max(1,len(result)//2)
    while width:
        i=0
        while i<len(result):
            candidate=result[:i]+result[i+width:]
            if fails(candidate):result=candidate
            else:i+=width
        width//=2
    return result
