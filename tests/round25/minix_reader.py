# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Independent, read-only Minix v1 payload reader; structural audit remains C fsck.
Supports this port's 1 KiB zones, 14-byte names and 16-bit zone pointers.
"""
import struct
from pathlib import Path
class ImageError(ValueError):pass
class MinixImage:
    def __init__(self,path):
        if Path(path).stat().st_size>128*1024*1024:raise ImageError('image exceeds 128 MiB inspection bound')
        self.image=Path(path).read_bytes()
        if len(self.image)<512 or self.image[510:512]!=b'\x55\xaa':raise ImageError('missing MBR')
        start,sectors=struct.unpack_from('<II',self.image,454)
        offset=start*512;size=sectors*512
        if not start or not size or offset+size>len(self.image):raise ImageError('partition bounds')
        self.fs=self.image[offset:offset+size]
        if len(self.fs)<2048:raise ImageError('short superblock')
        self.ninodes,self.nzones,self.imap,self.zmap,self.first,self.shift,self.maxsize,magic=struct.unpack_from('<6HIH',self.fs,1024)
        if magic!=0x137f or self.shift!=0:raise ImageError('unsupported Minix geometry')
        if not self.ninodes or self.nzones*1024>len(self.fs) or self.first>=self.nzones:raise ImageError('filesystem bounds')
        self.table=(2+self.imap+self.zmap)*1024
        if self.table+self.ninodes*32>self.first*1024:raise ImageError('inode table overlap')
    def inode(self,n):
        if not 1<=n<=self.ninodes:raise ImageError('inode bounds')
        fields=struct.unpack_from('<HHIIBB9H',self.fs,self.table+(n-1)*32)
        return {'mode':fields[0],'size':fields[2],'links':fields[5],'zones':fields[6:]}
    def zone(self,n):
        if not self.first<=n<self.nzones:raise ImageError('zone bounds')
        return self.fs[n*1024:(n+1)*1024]
    def pointer(self,n,index):return struct.unpack_from('<H',self.zone(n),index*2)[0] if n else 0
    def data(self,n):
        inode=self.inode(n);size=inode['size'];zones=inode['zones'];out=[]
        if size>8*1024*1024:raise ImageError('payload exceeds 8 MiB inspection bound')
        if size>self.maxsize or size>(7+512+512*512)*1024:raise ImageError('file size bounds')
        for index in range((size+1023)//1024):
            if index<7:zone=zones[index]
            elif index<519:zone=self.pointer(zones[7],index-7)
            else:
                tail=index-519;zone=self.pointer(self.pointer(zones[8],tail//512),tail%512)
            out.append(self.zone(zone) if zone else bytes(1024))
        return b''.join(out)[:size]
    def directory(self,n):
        if self.inode(n)['mode']&0xf000!=0x4000:raise ImageError('not directory')
        raw=self.data(n)
        if len(raw)%16:raise ImageError('partial directory entry')
        result={}
        for off in range(0,len(raw),16):
            ino,name=struct.unpack_from('<H14s',raw,off)
            if not ino:continue
            name=name.split(b'\0',1)[0].decode('ascii')
            if name in result:raise ImageError('duplicate directory name')
            if not 1<=ino<=self.ninodes:raise ImageError('directory inode bounds')
            result[name]=ino
        return result
    def resolve(self,path):
        if not path.startswith('/'):raise ImageError('absolute path required')
        ino=1
        for part in path.split('/')[1:]:
            if part=='':continue
            if part in ('.','..') or len(part.encode())>14:raise ImageError('invalid component')
            try:ino=self.directory(ino)[part]
            except KeyError:raise ImageError('path not found: '+path) from None
        return ino
    def read(self,path):return self.data(self.resolve(path))
