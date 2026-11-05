#include <errno.h>

#include <linux/sched.h>
#include <linux/tty.h>
#include <linux/kernel.h>
#include <linux/fs.h>
#include <linux/bemu.h>
#include <asm/segment.h>
#include <asm/io.h>
#include <asm/system.h>
#include <sys/times.h>
#include <sys/utsname.h>

struct ps_slot {
	int pid, ppid, state, counter, priority, uid, tty;
	long utime, stime;
};

struct ps_snapshot {
	int count;
	struct ps_slot slot[16];
};

int sys_ftime()
{
	return -ENOSYS;
}

int sys_mknod()
{
	return -ENOSYS;
}

int sys_break()
{
	return -ENOSYS;
}

int sys_mount()
{
	return -ENOSYS;
}

int sys_umount()
{
	return -ENOSYS;
}

int sys_ustat(int dev,struct ustat * ubuf)
{
	struct super_block * s;
	int i, free_blocks, free_inodes;

	if (!ubuf)
		return -1;
	if (verify_area(ubuf,sizeof *ubuf))
		return -EFAULT;
	if (!dev && current->root)
		dev = current->root->i_dev;
	for (s = super_block ; s < super_block + NR_SUPER ; s++)
		if (s->s_dev == dev)
			break;
	if (s >= super_block + NR_SUPER || !s->s_dev)
		return -1;
	free_blocks = 0;
	for (i = 1 ; i <= s->s_nzones-s->s_firstdatazone ; i++)
		if (!(s->s_zmap[i>>13]->b_data[(i&8191)>>3] & (1 << (i&7))))
			free_blocks++;
	free_inodes = 0;
	for (i = 0 ; i <= s->s_ninodes ; i++)
		if (!(s->s_imap[i>>13]->b_data[(i&8191)>>3] & (1 << (i&7))))
			free_inodes++;
	put_fs_long(free_blocks,(unsigned long *)&ubuf->f_tfree);
	put_fs_word(free_inodes,(short *)&ubuf->f_tinode);
	for (i = 0 ; i < 6 ; i++) {
		put_fs_byte(i < 5 ? "root"[i] : 0, ubuf->f_fname + i);
		put_fs_byte(0, ubuf->f_fpack + i);
	}
	return 0;
}

int sys_ptrace()
{
	return -ENOSYS;
}

int sys_stty()
{
	return -ENOSYS;
}

int sys_gtty()
{
	return -ENOSYS;
}

int sys_rename()
{
	return -ENOSYS;
}

int sys_prof(struct ps_snapshot * ubuf)
{
	int i, n = 0;
	struct task_struct * p;

	if (!ubuf)
		return -1;
	if (verify_area(ubuf,sizeof *ubuf))
		return -EFAULT;
	for (i = 0 ; i < NR_TASKS && n < 16 ; i++) {
		if (!(p = task[i]))
			continue;
		put_fs_long(p->pid,(unsigned long *)&ubuf->slot[n].pid);
		put_fs_long(p->father,(unsigned long *)&ubuf->slot[n].ppid);
		put_fs_long(p->state,(unsigned long *)&ubuf->slot[n].state);
		put_fs_long(p->counter,(unsigned long *)&ubuf->slot[n].counter);
		put_fs_long(p->priority,(unsigned long *)&ubuf->slot[n].priority);
		put_fs_long(p->uid,(unsigned long *)&ubuf->slot[n].uid);
		put_fs_long(p->tty,(unsigned long *)&ubuf->slot[n].tty);
		put_fs_long(p->utime,(unsigned long *)&ubuf->slot[n].utime);
		put_fs_long(p->stime,(unsigned long *)&ubuf->slot[n].stime);
		n++;
	}
	put_fs_long(n,(unsigned long *)&ubuf->count);
	return n;
}

int sys_setgid(int gid)
{
	if (current->euid && current->uid)
		if (current->gid==gid || current->sgid==gid)
			current->egid=gid;
		else
			return -EPERM;
	else
		current->gid=current->egid=gid;
	return 0;
}

int sys_acct()
{
	return -ENOSYS;
}

int sys_phys(int cmd)
{
	if (current->euid != 0)
		return -EPERM;
	cli();
	if (cmd == 1) {
		unsigned char good = 0x02;
		while (good & 0x02)
			good = inb_p(0x64);
		outb(0xfe,0x64);
	}
	outb(cmd == 1 ? BEMU_POWER_REBOOT : BEMU_POWER_HALT, BEMU_POWER_PORT);
	for (;;)
		__asm__("hlt");
}

int sys_lock()
{
	return -ENOSYS;
}

int sys_mpx()
{
	return -ENOSYS;
}

int sys_ulimit()
{
	return -ENOSYS;
}

int sys_time(long * tloc)
{
	int i;

	i = CURRENT_TIME;
	if (tloc) {
		if (verify_area(tloc,4))
			return -EFAULT;
		put_fs_long(i,(unsigned long *)tloc);
	}
	return i;
}

int sys_setuid(int uid)
{
	if (current->euid && current->uid)
		if (uid==current->uid || current->suid==current->uid)
			current->euid=uid;
		else
			return -EPERM;
	else
		current->euid=current->uid=uid;
	return 0;
}

int sys_stime(long * tptr)
{
	if (current->euid && current->uid)
		return -1;
	startup_time = get_fs_long((unsigned long *)tptr) - jiffies/HZ;
	return 0;
}

int sys_times(struct tms * tbuf)
{
	if (!tbuf)
		return jiffies;
	if (verify_area(tbuf,sizeof *tbuf))
		return -EFAULT;
	put_fs_long(current->utime,(unsigned long *)&tbuf->tms_utime);
	put_fs_long(current->stime,(unsigned long *)&tbuf->tms_stime);
	put_fs_long(current->cutime,(unsigned long *)&tbuf->tms_cutime);
	put_fs_long(current->cstime,(unsigned long *)&tbuf->tms_cstime);
	return jiffies;
}

int sys_brk(unsigned long end_data_seg)
{
	if (end_data_seg >= current->end_code &&
	    end_data_seg < current->start_stack - 16384)
		current->brk = end_data_seg;
	return current->brk;
}

/*
 * This needs some heave checking ...
 * I just haven't get the stomach for it. I also don't fully
 * understand sessions/pgrp etc. Let somebody who does explain it.
 */
int sys_setpgid(int pid, int pgid)
{
	int i;

	if (!pid)
		pid = current->pid;
	if (!pgid)
		pgid = pid;
	for (i=0 ; i<NR_TASKS ; i++)
		if (task[i] && task[i]->pid==pid) {
			if (task[i]->leader)
				return -EPERM;
			if (task[i]->session != current->session)
				return -EPERM;
			task[i]->pgrp = pgid;
			return 0;
		}
	return -ESRCH;
}

int sys_getpgrp(void)
{
	return current->pgrp;
}

int sys_setsid(void)
{
	if (current->uid && current->euid)
		return -EPERM;
	if (current->leader)
		return -EPERM;
	current->leader = 1;
	current->session = current->pgrp = current->pid;
	current->tty = -1;
	return current->pgrp;
}

int sys_uname(struct utsname * name)
{
	static struct utsname thisname = {
		"linux .0","nodename","release ","version ","machine "
	};
	int i;

	if (!name) return -1;
	if (verify_area(name,sizeof *name))
		return -EFAULT;
	for(i=0;i<sizeof *name;i++)
		put_fs_byte(((char *) &thisname)[i],i+(char *) name);
	return (0);
}

int sys_umask(int mask)
{
	int old = current->umask;

	current->umask = mask & 0777;
	return (old);
}
