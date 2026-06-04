"""
GDB Pretty-Printers for Linux 0.01 Kernel Structures.

Usage:
    (gdb) source gdb/printers.py
    (gdb) print current
    (gdb) print *task[0]
    (gdb) print *bh

Auto-loading: add to .gdbinit:
    source /path/to/linux-0.01-still-runs/gdb/printers.py
"""

import gdb
import re


def _field(ptr, field, typecast=None):
    """Dereference a pointer and read a field."""
    if ptr is None:
        return None
    try:
        ref = ptr.dereference()
        val = ref[field]
        if typecast:
            val = val.cast(typecast)
        return val
    except Exception:
        return None


def _read_c_string(addr, maxlen=64):
    """Read a null-terminated string from guest memory."""
    if addr is None:
        return "<nil>"
    try:
        addr_int = int(addr) if hasattr(addr, '__int__') else addr
        buf = gdb.selected_inferior().read_memory(addr_int, maxlen)
        s = bytes(buf).split(b'\x00')[0]
        return s.decode('ascii', errors='replace')
    except Exception:
        return "<?" ">"


TASK_STATE_NAMES = {
    0: "RUNNING",
    1: "INTERRUPTIBLE",
    2: "UNINTERRUPTIBLE",
    3: "ZOMBIE",
    4: "STOPPED",
}


class TaskStructPrinter:
    """Pretty-print struct task_struct."""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        pid = int(self.val['pid'])
        state = int(self.val['state'])
        state_name = TASK_STATE_NAMES.get(state, f"UNKNOWN({state})")
        counter = int(self.val['counter'])
        priority = int(self.val['priority'])
        signal = int(self.val['signal'])
        return (
            f"{{ pid={pid}, state={state_name}, "
            f"counter={counter}, priority={priority}, "
            f"signal=0x{signal:x} }}"
        )

    def children(self):
        yield 'pid', self.val['pid']
        yield 'state', self.val['state']
        yield 'counter', self.val['counter']
        yield 'priority', self.val['priority']
        yield 'signal', self.val['signal']
        yield 'exit_code', self.val['exit_code']
        yield 'father', self.val['father']
        yield 'pgrp', self.val['pgrp']
        yield 'session', self.val['session']
        yield 'leader', self.val['leader']
        yield 'alarm', self.val['alarm']
        yield 'uid', self.val['uid']
        yield 'euid', self.val['euid']
        yield 'tty', self.val['tty']
        yield 'umask', self.val['umask']
        yield 'pwd', self.val['pwd']
        yield 'root', self.val['root']
        yield 'start_time', self.val['start_time']
        yield 'utime', self.val['utime']
        yield 'stime', self.val['stime']
        yield 'cutime', self.val['cutime']
        yield 'cstime', self.val['cstime']


class BufferHeadPrinter:
    """Pretty-print struct buffer_head."""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        dev = int(self.val['b_dev'])
        block = int(self.val['b_blocknr'])
        uptodate = int(self.val['b_uptodate'])
        dirt = int(self.val['b_dirt'])
        count = int(self.val['b_count'])
        lock = int(self.val['b_lock'])
        return (
            f"{{ dev={dev}, block={block}, uptodate={uptodate}, "
            f"dirt={dirt}, count={count}, lock={lock} }}"
        )

    def children(self):
        yield '__dev', self.val['b_dev']
        yield '__blocknr', self.val['b_blocknr']
        yield '__b_uptodate', self.val['b_uptodate']
        yield '__b_dirt', self.val['b_dirt']
        yield '__b_count', self.val['b_count']
        yield '__b_lock', self.val['b_lock']
        yield '__b_data', self.val['b_data']
        yield '__b_wait', self.val['b_wait']


class MinixInodePrinter:
    """Pretty-print struct m_inode."""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        mode = int(self.val['i_mode'])
        size = int(self.val['i_size'])
        dev = int(self.val['i_dev'])
        num = int(self.val['i_num'])
        count = int(self.val['i_count'])
        type_str = "???"
        if mode & 0o100000:
            type_str = "REG"
        elif mode & 0o040000:
            type_str = "DIR"
        elif mode & 0o020000:
            type_str = "CHR"
        elif mode & 0o010000:
            type_str = "BLK"
        if self.val['i_pipe']:
            type_str = "PIPE"
        return (
            f"{{ ino={num}, dev={dev}, type={type_str}, "
            f"size={size}, count={count}, mode=0x{mode:o} }}"
        )

    def children(self):
        yield '__i_mode', self.val['i_mode']
        yield '__i_uid', self.val['i_uid']
        yield '__i_size', self.val['i_size']
        yield '__i_gid', self.val['i_gid']
        yield '__i_nlinks', self.val['i_nlinks']
        yield '__i_dev', self.val['i_dev']
        yield '__i_num', self.val['i_num']
        yield '__i_count', self.val['i_count']
        yield '__i_lock', self.val['i_lock']
        yield '__i_dirt', self.val['i_dirt']
        yield '__i_pipe', self.val['i_pipe']
        yield '__i_mount', self.val['i_mount']
        for i in range(9):
            yield f'i_zone[{i}]', self.val['i_zone'][i]


class FileStructPrinter:
    """Pretty-print struct file."""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        mode = int(self.val['f_mode'])
        flags = int(self.val['f_flags'])
        count = int(self.val['f_count'])
        pos = int(self.val['f_pos'])
        inode = self.val['f_inode']
        return (
            f"{{ mode=0x{mode:x}, flags=0x{flags:x}, "
            f"count={count}, pos={pos}, inode={inode} }}"
        )


class SuperBlockPrinter:
    """Pretty-print struct super_block."""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        dev = int(self.val['s_dev'])
        ninodes = int(self.val['s_ninodes'])
        nzones = int(self.val['s_nzones'])
        magic = int(self.val['s_magic'])
        return (
            f"{{ dev={dev}, ninodes={ninodes}, nzones={nzones}, "
            f"magic=0x{magic:x} }}"
        )


class PageDirPrinter:
    """Print the page directory at pg_dir (phys 0)."""

    name = "page_table"

    @staticmethod
    def invoke(gdb_stdout):
        try:
            pg_dir = int(gdb.parse_and_eval("&pg_dir"))
        except Exception:
            try:
                pg_dir = int(gdb.parse_and_eval("(unsigned long)0"))
            except Exception:
                gdb.write("pg_dir not found\n")
                return

        gdb.write(f"Page Directory @ 0x{pg_dir:08x}\n")
        gdb.write(f"{'Idx':>4} {'Addr':>10} {'Present':>8} {'RW':>4} {'User':>4}\n")
        gdb.write("-" * 40 + "\n")

        try:
            mem = gdb.selected_inferior().read_memory(pg_dir, 1024)
        except Exception as e:
            gdb.write(f"Cannot read page directory: {e}\n")
            return

        for i in range(256):
            entry = int.from_bytes(bytes(mem[i * 4:(i + 1) * 4]), 'little')
            if entry & 1:
                addr = entry & 0xFFFFF000
                present = "yes"
                rw = "W" if (entry & 2) else "R"
                user = "U" if (entry & 4) else "S"
                gdb.write(f"  {i:3d}  0x{addr:08x}  {present:>8}  {rw:>3}  {user:>3}\n")


class TaskListPrinter:
    """Print all tasks in the task array."""

    name = "task_list"

    @staticmethod
    def invoke(gdb_stdout):
        try:
            task_array = gdb.parse_and_eval("task")
            current_ptr = gdb.parse_and_eval("current")
        except Exception as e:
            gdb.write(f"Cannot read task array: {e}\n")
            return

        try:
            current_addr = int(current_ptr)
        except Exception:
            current_addr = 0

        gdb.write(f"{'Slot':>5} {'PID':>5} {'State':>16} {'Counter':>8} "
                  f"{'Priority':>8} {'Signal':>8} {'Current':>8}\n")
        gdb.write("-" * 70 + "\n")

        for i in range(64):
            ptr = task_array[i]
            if int(ptr) == 0:
                continue
            try:
                t = ptr.dereference()
                pid = int(t['pid'])
                state = int(t['state'])
                state_name = TASK_STATE_NAMES.get(state, f"U{state}")
                counter = int(t['counter'])
                priority = int(t['priority'])
                signal = int(t['signal'])
                is_current = "◄" if int(ptr) == current_addr else ""
                gdb.write(f"  {i:3d}  {pid:5d}  {state_name:>16}  {counter:8d}  "
                          f"{priority:8d}  0x{signal:06x}  {is_current:>8}\n")
            except Exception:
                pass


class BufferListPrinter:
    """Print all buffer_heads in the free list."""

    name = "buffer_list"

    @staticmethod
    def invoke(gdb_stdout):
        try:
            start_buf = gdb.parse_and_eval("start_buffer")
            nr_buf = int(gdb.parse_and_eval("nr_buffers"))
        except Exception as e:
            gdb.write(f"Cannot read buffer info: {e}\n")
            return

        gdb.write(f"Buffer cache: {nr_buf} buffers starting @ {start_buf}\n")
        gdb.write(f"{'Dev':>5} {'Block':>7} {'Uptodate':>9} {'Dirt':>5} "
                  f"{'Count':>6} {'Lock':>5}\n")
        gdb.write("-" * 45 + "\n")

        bh = start_buf
        for _ in range(min(nr_buf, 300)):
            try:
                dev = int(bh['b_dev'])
                block = int(bh['b_blocknr'])
                up = int(bh['b_uptodate'])
                dirt = int(bh['b_dirt'])
                cnt = int(bh['b_count'])
                lock = int(bh['b_lock'])
                gdb.write(f"  {dev:3d}  {block:7d}  {up:9d}  {dirt:5d}  "
                          f"{cnt:6d}  {lock:5d}\n")
            except Exception:
                break
            try:
                bh = bh['b_next_free']
                if int(bh) == int(start_buf):
                    break
            except Exception:
                break


# -----------------------------------------------------------------------
# Register printers with GDB
# -----------------------------------------------------------------------

def register_printers():
    """Register all pretty-printers and commands."""

    tag = "linux-0.01"

    gdb.printing.register_pretty_printer(
        gdb.selected_inferior(),
        gdb.printing.RegexpCollectionPrettyPrinter(tag)
    )

    pp = gdb.printing.RegexpCollectionPrettyPrinter(tag)
    pp.add_printer('task_struct', '^task_struct$', TaskStructPrinter)
    pp.add_printer('buffer_head', '^buffer_head$', BufferHeadPrinter)
    pp.add_printer('m_inode', '^m_inode$', MinixInodePrinter)
    pp.add_printer('file', '^file$', FileStructPrinter)
    pp.add_printer('super_block', '^super_block$', SuperBlockPrinter)

    gdb.printing.register_pretty_printer(gdb.selected_inferior(), pp)

    class PageTableCommand(gdb.Command):
        """Print the i386 page directory. Usage: page_table"""

        def __init__(self):
            super().__init__("page_table", gdb.COMMAND_USER)

        def invoke(self, arg, from_tty):
            PageDirPrinter.invoke(gdb.stdout)

    class TaskListCommand(gdb.Command):
        """Print all processes. Usage: task_list"""

        def __init__(self):
            super().__init__("task_list", gdb.COMMAND_USER)

        def invoke(self, arg, from_tty):
            TaskListPrinter.invoke(gdb.stdout)

    class BufferListCommand(gdb.Command):
        """Print buffer cache. Usage: buffer_list"""

        def __init__(self):
            super().__init__("buffer_list", gdb.COMMAND_USER)

        def invoke(self, arg, from_tty):
            BufferListPrinter.invoke(gdb.stdout)

    PageTableCommand()
    TaskListCommand()
    BufferListCommand()

    gdb.write("linux-0.01 GDB pretty-printers loaded.\n")
    gdb.write("  Commands: page_table  task_list  buffer_list\n")


register_printers()
