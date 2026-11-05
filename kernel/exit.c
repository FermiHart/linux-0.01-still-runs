#include <errno.h>
#include <signal.h>
#include <sys/wait.h>

#include <linux/sched.h>
#include <linux/kernel.h>
#include <linux/tty.h>
#include <asm/segment.h>

int sys_pause(void);
int sys_close(int fd);

static unsigned long current_base(void)
{
	unsigned long base;
	int nr;

	base = get_base(current->ldt[1]);
	if (current == task[0])
		return base;
	nr = (current->tss.ldt - (FIRST_LDT_ENTRY << 3)) >> 4;
	if (nr <= 0 || nr >= NR_TASKS)
		return base;
	if (base == nr * 0x4000000)
		return base;
	base = nr * 0x4000000;
	set_base(current->ldt[1],base);
	set_base(current->ldt[2],base);
	return base;
}

void release(struct task_struct * p)
{
	int i;

	if (!p)
		return;
	for (i=1 ; i<NR_TASKS ; i++)
		if (task[i]==p) {
			task[i]=NULL;
			free_page((long)p);
			schedule();
			return;
		}
	panic("trying to release non-existent task");
}

static inline void send_sig(long sig,struct task_struct * p,int priv)
{
	if (!p || sig<1 || sig>32)
		return;
	if (priv ||
		current->uid==p->uid ||
		current->euid==p->uid ||
		current->uid==p->euid ||
		current->euid==p->euid)
		p->signal |= (1<<(sig-1));
}

int do_kill(long pid,long sig,int priv)
{
	struct task_struct **p = NR_TASKS + task;
	int found = 0;

	if (!pid) while (--p > &FIRST_TASK) {
		if (*p && (*p)->pgrp == current->pid) {
			send_sig(sig,*p,priv);
			found++;
		}
	} else if (pid>0) while (--p > &FIRST_TASK) {
		if (*p && (*p)->pid == pid) {
			send_sig(sig,*p,priv);
			found++;
		}
	} else if (pid == -1) while (--p > &FIRST_TASK)
		send_sig(sig,*p,priv);
	else while (--p > &FIRST_TASK)
		if (*p && (*p)->pgrp == -pid) {
			send_sig(sig,*p,priv);
			found++;
		}
	return found ? 0 : -ESRCH;
}

int sys_kill(int pid,int sig)
{
	return do_kill(pid,sig,!(current->uid || current->euid));
}

int do_exit(long code)
{
	int i;

	free_page_tables(current_base(),get_limit(0x0f));
	free_page_tables(current_base(),get_limit(0x17));
	for (i=0 ; i<NR_TASKS ; i++)
		if (task[i] && task[i]->father == current->pid)
			task[i]->father = 0;
	for (i=0 ; i<NR_OPEN ; i++)
		if (current->filp[i])
			sys_close(i);
	iput(current->pwd);
	current->pwd=NULL;
	iput(current->root);
	current->root=NULL;
	if (current->leader && current->tty >= 0 && current->tty < NR_TTYS)
		tty_table[current->tty].pgrp = 0;
	if (last_task_used_math == current)
		last_task_used_math = NULL;
	if (current->father) {
		current->state = TASK_ZOMBIE;
		do_kill(current->father,SIGCHLD,1);
		current->exit_code = code;
	} else
		release(current);
	schedule();
	return (-1);	/* just to suppress warnings */
}

int sys_exit(int error_code)
{
	return do_exit((error_code&0xff)<<8);
}

int sys_waitpid(pid_t pid,int * stat_addr, int options)
{
	int flag=0;
	struct task_struct ** p;

	if (stat_addr && verify_area(stat_addr,4))
		return -EFAULT;
repeat:
	for(p = &LAST_TASK ; p > &FIRST_TASK ; --p)
		if (*p && *p != current &&
		   (pid==-1 || (*p)->pid==pid ||
		   (pid==0 && (*p)->pgrp==current->pgrp) ||
		   (pid<0 && (*p)->pgrp==-pid)))
			if ((*p)->father == current->pid) {
				flag=1;
				if ((*p)->state==TASK_ZOMBIE) {
					if (stat_addr)
						put_fs_long((*p)->exit_code,
							(unsigned long *) stat_addr);
					current->cutime += (*p)->utime;
					current->cstime += (*p)->stime;
					flag = (*p)->pid;
					release(*p);
					return flag;
				}
			}
	if (flag) {
		if (options & WNOHANG)
			return 0;
		sys_pause();
		if (!(current->signal &= ~(1<<(SIGCHLD-1))))
			goto repeat;
		else
			return -EINTR;
	}
	return -ECHILD;
}
