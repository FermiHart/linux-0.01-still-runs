#!/usr/bin/env python3
# Author: F E R M I ∞ H A R T <contact@fermihart.com>
# SPDX-License-Identifier: Unlicense
"""Execute extracted production contracts on the host, never a guest boot.

The function bodies/macro block are read from the working source unchanged.
Kernel scheduling, segmentation and allocator boundaries are stubbed explicitly.
"""
import os
import re
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def function(path, name):
    text = (ROOT / path).read_text()
    match = re.search(r'(?m)^[A-Za-z][\w \t*]*\b' + re.escape(name) + r'\(', text)
    if not match: raise ValueError(f'function {name} not found in {path}')
    start = pos = match.start()
    brace = text.index('{', pos)
    depth = 1
    end = brace + 1
    while depth:
        if text[end] == '{': depth += 1
        if text[end] == '}': depth -= 1
        end += 1
    return text[start:end] + '\n'


def c_run(body, opt='-O2', sanitize=False):
    with tempfile.TemporaryDirectory(prefix='linux001-contract-') as directory:
        source, binary = Path(directory)/'case.c', Path(directory)/'case'
        source.write_text(body)
        flags = ['-std=gnu99', '-Wall', '-Wextra', '-Werror', opt]
        if sanitize:
            flags += ['-fsanitize=undefined', '-fno-sanitize-recover=all']
        build = subprocess.run([os.environ.get('HOSTCC', 'cc'), *flags,
                                str(source), '-o', str(binary)], capture_output=True, text=True, timeout=30)
        if build.returncode:
            raise AssertionError(build.stderr)
        run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
        if run.returncode:
            raise AssertionError(f'host status {run.returncode}: {run.stdout}{run.stderr}')
        return run.stdout


class Contracts(unittest.TestCase):
    def test_crt0_return_uses_register_argument(self):
        # This checks the assembled production sequence, not Linux 0.01 execution.
        with tempfile.TemporaryDirectory() as d:
            obj = Path(d)/'crt0.o'
            subprocess.run(['as', '--32', str(ROOT/'userland/crt0.S'), '-o', str(obj)], check=True)
            asm = subprocess.check_output(['objdump', '-dr', str(obj)], text=True)
            tail = asm[asm.index('R_386_PC32\t_main'):]
            self.assertRegex(tail, r'mov\s+%eax,%ebx')
            self.assertLess(tail.index('%eax,%ebx'), tail.index('$0x1,%eax'))

    def test_dup2_preserves_source_and_validates_before_close(self):
        body = '''
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#define NR_OPEN 20
struct file { int f_count; };
struct task { struct file *filp[NR_OPEN]; unsigned close_on_exec; } state;
struct task *current = &state;
static int closes;
int sys_close(unsigned fd) {
    if (fd >= NR_OPEN || !current->filp[fd]) return -EBADF;
    ++closes; --current->filp[fd]->f_count; current->filp[fd] = 0;
    current->close_on_exec &= ~(1U << fd); return 0;
}
'''
        body += function('fs/fcntl.c', 'dupfd') + function('fs/fcntl.c', 'sys_dup2')
        body += '''
int main(void) {
    struct file a={1}, b={1}; int i;
    state.filp[3]=&a; state.filp[5]=&b; state.close_on_exec=1U<<3;
    assert(sys_dup2(3,3)==3); assert(a.f_count==1); assert(closes==0);
    assert(state.close_on_exec==(1U<<3));
    assert(sys_dup2(4,5)==-EBADF); assert(state.filp[5]==&b); assert(closes==0);
    assert(sys_dup2(3,NR_OPEN)==-EBADF); assert(closes==0);
    assert(sys_dup2(3,5)==5); assert(closes==1); assert(a.f_count==2); assert(!b.f_count);
    for(i=0;i<NR_OPEN;i++) if(!state.filp[i]) { state.filp[i]=&a; a.f_count++; }
    assert(dupfd(3,0)==-EMFILE);
    assert(sys_dup2(3,6)==6); assert(a.f_count==NR_OPEN); /* replace at fd exhaustion */
    return 0;
}
'''
        for opt in ('-O0', '-O1', '-O2', '-Os'):
            with self.subTest(opt=opt): c_run(body, opt, True)

    def test_bitmap_memory_register_and_flag_contracts(self):
        source=(ROOT/'fs/bitmap.c').read_text()
        macros=source[source.index('#define clear_block'):source.index('static struct super_block')]
        body='''
#include <assert.h>
#include <string.h>
#define BLOCK_SIZE 1024
'''+macros+'''
static unsigned int bitmap[256];
static __attribute__((noinline)) int test(void) {
    int n;
    clear_block(bitmap);
    assert(find_first_zero(bitmap)==0);
    for(n=0;n<8192;n++) {
        assert(set_bit(n,bitmap)==0);
        assert(bitmap[n/32] & (1U<<(n%32)));
        assert(set_bit(n,bitmap)==1);
    }
    assert(find_first_zero(bitmap)==8192);
    assert(clear_bit(4097,bitmap)==0);
    assert(find_first_zero(bitmap)==4097);
    assert(clear_bit(4097,bitmap)==1);
    clear_block(bitmap);
    for(n=0;n<256;n++) assert(bitmap[n]==0);
    return 0;
}
int main(void) { return test(); }
'''
        for opt in ('-O0', '-O1', '-O2', '-Os'):
            with self.subTest(opt=opt): c_run(body,opt)


class MemoryContracts(unittest.TestCase):
    def test_free_page_exclusive_upper_bound_and_underflow(self):
        body='''
#include <assert.h>
#include <setjmp.h>
#include <stddef.h>
#define LOW_MEM 0x100000UL
#define HIGH_MEMORY 0x110000UL
#define PAGING_PAGES ((HIGH_MEMORY-LOW_MEM)/4096)
static unsigned short mem_map[PAGING_PAGES];
static jmp_buf trap;
static void panic(const char *reason) { (void)reason; longjmp(trap,1); }
'''+function('mm/memory.c','free_page')+'''
int main(void) {
    if (!setjmp(trap)) { free_page(HIGH_MEMORY); assert(0); }
    if (!setjmp(trap)) { free_page(LOW_MEM+1); assert(0); }
    mem_map[0]=2; free_page(LOW_MEM); assert(mem_map[0]==1);
    free_page(LOW_MEM); assert(mem_map[0]==0);
    if (!setjmp(trap)) { free_page(LOW_MEM); assert(0); }
    assert(mem_map[0]==0); free_page(0);
    return 0;
}
'''
        c_run(body,sanitize=True)

    def test_put_page_rejects_before_page_table_or_refcount_access(self):
        body='''
#include <assert.h>
#include <stddef.h>
#define LOW_MEM 0x100000UL
#define HIGH_MEMORY 0x110000UL
static unsigned short mem_map[16];
static int printk(const char *format,...) { (void)format; return 0; }
static unsigned long get_free_page(void) { assert(0); return 0; }
'''+function('mm/memory.c','put_page')+'''
int main(void) {
    assert(put_page(HIGH_MEMORY,0)==0);
    assert(put_page(0,0)==0);
    assert(put_page(LOW_MEM+1,0)==0);
    assert(put_page(LOW_MEM,0)==0); /* zero refcount must not install */
    return 0;
}
'''
        c_run(body,sanitize=True)

class PipeContracts(unittest.TestCase):
    def test_eof_sigpipe_and_close_during_block(self):
        body=r'''
#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <string.h>
struct task { unsigned signal; } state;
static struct task *current=&state;
struct m_inode { unsigned long i_size; unsigned i_count; int i_wait; unsigned head,tail; };
#define PIPE_HEAD(i) ((i).head)
#define PIPE_TAIL(i) ((i).tail)
#define INC_PIPE(x) ((x)=((x)+1)&4095)
#define PIPE_EMPTY(i) ((i).head==(i).tail)
#define PIPE_FULL(i) ((((i).head+1)&4095)==(i).tail)
static struct m_inode *sleep_inode;
static unsigned sleeps;
static void wake_up(int *p) { (void)p; }
static void sleep_on(int *p) { (void)p; ++sleeps; assert(sleeps<3); sleep_inode->i_count=1; }
static void put_fs_byte(char v,char *p) { *p=v; }
static char get_fs_byte(const char *p) { return *p; }
'''+function('fs/pipe.c','read_pipe')+function('fs/pipe.c','write_pipe')+r'''
int main(void) {
    char data[4096]={0}, out[8]={0}; struct m_inode inode={(unsigned long)data,1,0,0,0};
    sleep_inode=&inode;
    assert(read_pipe(&inode,out,1)==0); assert(!sleeps);
    assert(write_pipe(&inode,"x",1)==-EPIPE); assert(state.signal&(1U<<(SIGPIPE-1)));
    inode.i_count=2; state.signal=0;
    assert(write_pipe(&inode,"abc",3)==3);
    inode.i_count=1; assert(read_pipe(&inode,out,3)==3); assert(!memcmp(out,"abc",3));
    assert(read_pipe(&inode,out,1)==0);
    inode.i_count=2; inode.head=4095; inode.tail=0; sleeps=0; state.signal=0;
    assert(write_pipe(&inode,"x",1)==-EPIPE); assert(sleeps==1); assert(state.signal);
    inode.i_count=2; inode.head=4094; inode.tail=0; sleeps=0; state.signal=0;
    assert(write_pipe(&inode,"xy",2)==1); assert(sleeps==1); assert(state.signal);
    inode.i_count=2; inode.head=inode.tail=0; sleeps=0;
    assert(read_pipe(&inode,out,1)==0); assert(sleeps==1);
    return 0;
}
'''
        c_run(body,sanitize=True)

class UserRangeContracts(unittest.TestCase):
    def test_range_overflow_and_cow_pages(self):
        body=r'''
#include <assert.h>
#include <errno.h>
#include <limits.h>
static unsigned long user_limit=0xffffffffUL,segment_base;
static unsigned long visits,first,last;
#define get_limit(selector) ((void)(selector),user_limit)
#define get_base(segment) (segment_base)
static void write_verify(unsigned long page) { if(!visits) first=page; last=page; visits++; }
'''+function('kernel/fork.c','verify_read_area')+function('kernel/fork.c','verify_area')+r'''
int main(void) {
    assert(verify_read_area(0,1)==-EFAULT);
    assert(verify_read_area((void*)1,-1)==-EFAULT);
    assert(!verify_read_area((void*)1,0));
    assert(verify_read_area((void*)0xffffffffUL,1)==-EFAULT);
    assert(verify_read_area((void*)0xfffffffeUL,2)==-EFAULT);
    assert(!verify_read_area((void*)0xfffffffeUL,1));
    segment_base=ULONG_MAX-4096;
    assert(verify_read_area((void*)4096,2)==-EFAULT); segment_base=0;
    assert(!verify_area((void*)4095,2)); assert(visits==2 && first==0 && last==4096);
    visits=0; assert(!verify_area((void*)4095,INT_MAX)); assert(visits==524289);
    visits=0; assert(!verify_read_area((void*)4095,INT_MAX)); assert(!visits);
    user_limit=0x4000000; assert(verify_read_area((void*)4095,INT_MAX)==-EFAULT);
    return 0;
}
'''
        c_run(body,sanitize=True)

class CowContracts(unittest.TestCase):
    def test_production_cow_shared_unique_and_oom(self):
        body=r'''
#include <assert.h>
#include <signal.h>
#include <setjmp.h>
#define LOW_MEM 0x100000UL
#define MAP_NR(addr) (((addr)-LOW_MEM)>>12)
static unsigned short mem_map[16];
static unsigned long allocation,copy_from,copy_to;
static jmp_buf trap;
static unsigned long get_free_page(void) { return allocation; }
static void copy_page(unsigned long from,unsigned long to) { copy_from=from; copy_to=to; }
static int do_exit(long code) { assert(code==SIGSEGV); longjmp(trap,1); }
'''+function('mm/memory.c','un_wp_page')+r'''
int main(void) {
    unsigned long entry=LOW_MEM|5;
    mem_map[0]=1; un_wp_page(&entry); assert(entry==(LOW_MEM|7)); assert(!copy_to);
    mem_map[0]=2; mem_map[1]=1; entry=LOW_MEM|5; allocation=LOW_MEM+4096;
    un_wp_page(&entry); assert(entry==(allocation|7)); assert(mem_map[0]==1);
    assert(copy_from==LOW_MEM && copy_to==allocation);
    mem_map[0]=2; entry=LOW_MEM|5; allocation=0; copy_to=0;
    if(!setjmp(trap)) { un_wp_page(&entry); assert(0); }
    assert(entry==(LOW_MEM|5)); assert(mem_map[0]==2); assert(!copy_to);
    return 0;
}
'''
        c_run(body,sanitize=True)

    def test_fork_page_table_failure_cleanup(self):
        body=r'''
#include <assert.h>
#include <errno.h>
struct task_struct { unsigned long ldt[3]; } state,child;
static struct task_struct *current=&state;
#define get_limit(s) ((void)(s),0x4000000UL)
#define get_base(d) (d)
#define set_base(d,b) ((d)=(b))
static int failure,freed;
static void panic(const char *s) { (void)s; assert(0); }
static int copy_page_tables(unsigned long from,unsigned long to,unsigned long size) {
    assert(from==0x4000000 && to==0x8000000 && size==0x4000000); return failure;
}
static int free_page_tables(unsigned long from,unsigned long size) {
    assert(from==0x8000000 && size==0x4000000); freed++; return 0;
}
'''+function('kernel/fork.c','copy_mem')+r'''
int main(void) {
    state.ldt[1]=state.ldt[2]=0x4000000; failure=-1;
    assert(copy_mem(2,&child)==-ENOMEM); assert(freed==1);
    failure=0; assert(!copy_mem(2,&child)); assert(freed==1);
    assert(child.ldt[1]==0x8000000 && child.ldt[2]==0x8000000);
    return 0;
}
'''
        c_run(body,sanitize=True)

class WaitContracts(unittest.TestCase):
    def test_wait_reaps_once_null_status_and_interrupt(self):
        body=r'''
#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stddef.h>
#include <sys/types.h>
#include <sys/wait.h>
#define NR_TASKS 4
#define TASK_ZOMBIE 3
struct task_struct { int pid,pgrp,father,state,exit_code; unsigned long utime,stime,cutime,cstime; unsigned signal; } parent,child,other;
static struct task_struct *task[NR_TASKS], *current=&parent;
#define FIRST_TASK task[0]
#define LAST_TASK task[NR_TASKS-1]
static int released,bad_pointer;
static int verify_area(void *p,int n) { (void)p; assert(n==4); return bad_pointer; }
static void put_fs_long(unsigned long n,unsigned long *p) { *(uint32_t*)p=(uint32_t)n; }
static void release(struct task_struct *p) { int i; released++; for(i=1;i<NR_TASKS;i++) if(task[i]==p) task[i]=0; }
static int sys_pause(void) { current->signal=1U<<(SIGINT-1); return 0; }
'''+function('kernel/exit.c','sys_waitpid')+r'''
int main(void) {
    int status=0; parent.pid=10; parent.pgrp=7;
    child.pid=11; child.pgrp=7; child.father=10; child.state=TASK_ZOMBIE; child.exit_code=37<<8;
    child.utime=3; child.stime=4; task[1]=&child;
    bad_pointer=1; assert(sys_waitpid(-1,&status,0)==-EFAULT); assert(!released); bad_pointer=0;
    assert(sys_waitpid(0,&status,0)==11); assert(status==37<<8); assert(released==1);
    assert(parent.cutime==3 && parent.cstime==4); assert(sys_waitpid(-1,0,0)==-ECHILD);
    task[1]=&child; child.state=0; assert(sys_waitpid(-1,0,WNOHANG)==0);
    assert(sys_waitpid(-1,0,0)==-EINTR);
    child.state=TASK_ZOMBIE; assert(sys_waitpid(-7,0,0)==11); assert(released==2);
    other.pid=12; other.father=99; task[2]=&other; assert(sys_waitpid(-1,0,0)==-ECHILD);
    return 0;
}
'''
        c_run(body,sanitize=True)

class DescriptorContracts(unittest.TestCase):
    def test_descriptor_bytes_and_neighbor_preservation(self):
        body=r'''
#include <assert.h>
#include <string.h>
#include "'''+str(ROOT/'include/asm/system.h')+r'''"
int main(void) {
    unsigned char bytes[24]; unsigned char expected[8]={104,0,0x78,0x56,0x34,0x89,0,0x12};
    unsigned int gate[2]={0};
    memset(bytes,0xa5,sizeof(bytes));
    set_tss_desc(bytes+8,(void*)0x12345678UL);
    assert(!memcmp(bytes+8,expected,8)); assert(bytes[7]==0xa5 && bytes[16]==0xa5);
    set_ldt_desc(bytes+8,(void*)0xabcdef01UL);
    assert(bytes[10]==1 && bytes[11]==0xef && bytes[12]==0xcd && bytes[13]==0x82 && bytes[15]==0xab);
    _set_gate(gate,14,0,(void*)0x12345678UL);
    assert(gate[0]==0x00085678U && gate[1]==0x12348e00U);
    return 0;
}
'''
        for opt in ('-O0','-O1','-O2','-Os'):
            with self.subTest(opt=opt):c_run(body,opt)


class PageFaultOomContracts(unittest.TestCase):
    def test_unmapped_allocation_is_freed_on_page_table_oom(self):
        body=r"""
#include <assert.h>
#include <setjmp.h>
#include <signal.h>
#pragma GCC diagnostic ignored "-Wunused-parameter"
static int can_allocate,can_map,live,freed;
static jmp_buf trap;
static unsigned long get_free_page(void) { if(!can_allocate)return 0;live++;return 0x200000UL; }
static unsigned long put_page(unsigned long page,unsigned long address) {
    assert(page==0x200000UL && address==0x4001000UL); return can_map?page:0;
}
static __attribute__((unused)) void free_page(unsigned long page) { assert(page==0x200000UL && live==1);live--;freed++; }
static int do_exit(long code) { assert(code==SIGSEGV);longjmp(trap,1); }
"""+function('mm/memory.c','do_no_page')+r"""
int main(void) {
    can_allocate=1;can_map=0;
    if(!setjmp(trap)) { do_no_page(0,0x4001000UL);assert(0); }
    assert(live==0 && freed==1);
    can_allocate=0;
    if(!setjmp(trap)) { do_no_page(0,0x4001000UL);assert(0); }
    assert(live==0 && freed==1);
    can_allocate=can_map=1;do_no_page(0,0x4001000UL);
    assert(live==1 && freed==1); /* ownership transferred to the installed PTE */
    return 0;
}
"""
        c_run(body,sanitize=True)

if __name__ == '__main__': unittest.main(verbosity=2)
