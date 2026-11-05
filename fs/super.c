/*
 * super.c contains code to handle the super-block tables.
 */
#include <linux/config.h>
#include <linux/sched.h>
#include <linux/kernel.h>
#include <linux/fs.h>

extern struct m_inode inode_table[];

/* set_bit uses setb, as gas doesn't recognize setc */
#define set_bit(bitnr,addr) ({ \
register int __res; \
__asm__("bt %2,%3;setb %%al":"=a" (__res):"a" (0),"r" (bitnr),"m" (*(addr))); \
__res; })

#define test_bit(bitnr,addr) ({ \
register int __res; \
__asm__("bt %2,%3;setb %%al":"=a" (__res):"a" (0),"r" (bitnr),"m" (*(addr))); \
__res; })

struct super_block super_block[NR_SUPER];

struct super_block * do_mount(int dev)
{
	struct super_block * p;
	struct super_block * disk;
	struct buffer_head * bh;
	unsigned long inode_blocks, zone_bits;
	int i,block,bad;

	for(p = &super_block[0] ; p < &super_block[NR_SUPER] ; p++ )
		if (!(p->s_dev))
			break;
	if (p >= &super_block[NR_SUPER])
		return NULL;
	p->s_dev = -1;		/* mark it in use */
	if (!(bh = bread(dev,1))) {
		p->s_dev = 0;
		return NULL;
	}
	disk = (struct super_block *) bh->b_data;
	p->s_ninodes = disk->s_ninodes;
	p->s_nzones = disk->s_nzones;
	p->s_imap_blocks = disk->s_imap_blocks;
	p->s_zmap_blocks = disk->s_zmap_blocks;
	p->s_firstdatazone = disk->s_firstdatazone;
	p->s_log_zone_size = disk->s_log_zone_size;
	p->s_max_size = disk->s_max_size;
	p->s_magic = disk->s_magic;
	brelse(bh);
	for (i=0;i<I_MAP_SLOTS;i++)
		p->s_imap[i] = NULL;
	for (i=0;i<Z_MAP_SLOTS;i++)
		p->s_zmap[i] = NULL;
	inode_blocks = (p->s_ninodes + INODES_PER_BLOCK - 1) /
		INODES_PER_BLOCK;
	bad = p->s_magic != SUPER_MAGIC || !p->s_ninodes ||
		!p->s_imap_blocks || p->s_imap_blocks > I_MAP_SLOTS ||
		!p->s_zmap_blocks || p->s_zmap_blocks > Z_MAP_SLOTS ||
		p->s_log_zone_size ||
		(unsigned long)p->s_ninodes + 1 >
			(unsigned long)p->s_imap_blocks * BLOCK_SIZE * 8 ||
		p->s_firstdatazone < 2 + p->s_imap_blocks +
			p->s_zmap_blocks + inode_blocks ||
		p->s_firstdatazone >= p->s_nzones;
	zone_bits = (unsigned long)p->s_nzones - p->s_firstdatazone + 1;
	if (bad || zone_bits >
	    (unsigned long)p->s_zmap_blocks * BLOCK_SIZE * 8) {
		p->s_dev = 0;
		return NULL;
	}
	block=2;
	for (i=0 ; i < p->s_imap_blocks ; i++)
		if ((p->s_imap[i]=bread(dev,block)))
			block++;
		else
			break;
	for (i=0 ; i < p->s_zmap_blocks ; i++)
		if ((p->s_zmap[i]=bread(dev,block)))
			block++;
		else
			break;
	if (block != 2+p->s_imap_blocks+p->s_zmap_blocks) {
		for(i=0;i<I_MAP_SLOTS;i++)
			brelse(p->s_imap[i]);
		for(i=0;i<Z_MAP_SLOTS;i++)
			brelse(p->s_zmap[i]);
		p->s_dev=0;
		return NULL;
	}
	p->s_imap[0]->b_data[0] |= 1;
	p->s_zmap[0]->b_data[0] |= 1;
	p->s_dev = dev;
	p->s_isup = NULL;
	p->s_imount = NULL;
	p->s_time = 0;
	p->s_rd_only = 0;
	p->s_dirt = 0;
	return p;
}

void mount_root(void)
{
	int i,free;
	struct super_block * p;
	struct m_inode * mi;

	if (32 != sizeof (struct d_inode))
		panic("bad i-node size");
	for(i=0;i<NR_FILE;i++)
		file_table[i].f_count=0;
	for(p = &super_block[0] ; p < &super_block[NR_SUPER] ; p++)
		p->s_dev = 0;
	if (!(p=do_mount(ROOT_DEV)))
		panic("Unable to mount root");
	if (!(mi=iget(ROOT_DEV,1)))
		panic("Unable to read root i-node");
	mi->i_count += 3 ; /* NOTE! it is logically used 4 times, not 1 */
	p->s_isup = p->s_imount = mi;
	current->pwd = mi;
	current->root = mi;
	free=0;
	i=p->s_nzones-p->s_firstdatazone;
	while (i > 0) {
		if (!test_bit(i&8191,p->s_zmap[i>>13]->b_data))
			free++;
		i--;
	}
	printk("\033[32m%d\033[0m/\033[37m%d\033[0m free blocks\n\r",free,p->s_nzones);
	free=0;
	i=p->s_ninodes+1;
	while (-- i >= 0)
		if (!test_bit(i&8191,p->s_imap[i>>13]->b_data))
			free++;
	printk("\033[32m%d\033[0m/\033[37m%d\033[0m free inodes\n\r",free,p->s_ninodes);
}
