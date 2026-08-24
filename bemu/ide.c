#include "ide.h"
#include "experience.h"
#include "machine.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

extern void die(const char *what);
extern void fail(const char *what);

void ide_reset(struct ide_state *ide)
{
    ide->error = 1;
    ide->count = 0;
    ide->sector = 1;
    ide->lcyl = 0;
    ide->hcyl = 0;
    ide->current = 0xa0;
    ide->status = IDE_READY | IDE_SEEK;
    ide->control = 0;
    ide->lba = 0;
    ide->remaining = 0;
    ide->data_pos = 0;
    ide->writing = 0;
    ide->irq_pending = 0;
}

void map_disk(struct ide_state *ide, const char *path)
{
    struct stat st;
    int fd = open(path, O_RDWR);
    size_t expected = (size_t)IDE_CYLINDERS * IDE_HEADS * IDE_SECTORS * IDE_SECTOR_LEN;
    if (fd < 0)
        die(path);
    if (fstat(fd, &st) < 0)
        die("fstat root image");
    if ((size_t)st.st_size != expected)
        fail("root image does not match 977/5/17 CHS geometry");
    ide->disk = mmap(NULL, expected, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (ide->disk == MAP_FAILED) {
        int error = errno;
        (void)close(fd);
        errno = error;
        die("mmap root image");
    }
    if (close(fd) < 0)
        die("close root image");
    ide->disk_size = expected;
    ide_reset(ide);
}

int ide_experience_matches(const struct ide_state *ide, const char *experience)
{
    int historical = ide->disk_size >= EXPERIENCE_IMAGE_MARKER_OFFSET +
                      EXPERIENCE_IMAGE_MARKER_LEN &&
        memcmp(ide->disk + EXPERIENCE_IMAGE_MARKER_OFFSET,
               EXPERIENCE_IMAGE_MARKER_1991,
               EXPERIENCE_IMAGE_MARKER_LEN) == 0;

    if (experience && strcmp(experience, EXPERIENCE_1991) == 0)
        return historical;
    return !historical;
}

static void ide_set_irq(struct machine *m)
{
    struct ide_state *d = &m->ide;
    d->irq_pending = 1;
    if (!(d->control & 2))
        irq_level(m, 14, 1);
}

void ide_clear_irq(struct machine *m)
{
    m->ide.irq_pending = 0;
    irq_level(m, 14, 0);
}

static int ide_address(struct ide_state *d, uint32_t *lba)
{
    unsigned cyl = d->lcyl | ((unsigned)d->hcyl << 8);
    unsigned head = d->current & 15;
    if ((d->current & 0x10) || cyl >= IDE_CYLINDERS || head >= IDE_HEADS ||
        d->sector < 1 || d->sector > IDE_SECTORS)
        return -1;
    *lba = ((cyl * IDE_HEADS + head) * IDE_SECTORS) + d->sector - 1;
    return ((uint64_t)*lba * IDE_SECTOR_LEN < d->disk_size) ? 0 : -1;
}

static void ide_abort(struct machine *m)
{
    m->ide.error = 4;
    m->ide.status = IDE_READY | IDE_SEEK | IDE_ERR;
    m->ide.remaining = 0;
    m->ide.data_pos = 0;
    ide_set_irq(m);
}

void ide_command(struct machine *m, uint8_t command)
{
    struct ide_state *d = &m->ide;
    uint32_t lba;
    ide_clear_irq(m);
    if (command == 0x20 || command == 0x30) {
        if (ide_address(d, &lba) < 0) {
            ide_abort(m);
            return;
        }
        d->lba = lba;
        d->remaining = d->count ? d->count : 256;
        d->data_pos = 0;
        d->writing = command == 0x30;
        d->error = 0;
        d->status = IDE_READY | IDE_SEEK | IDE_DRQ;
        if (!d->writing)
            ide_set_irq(m);
        return;
    }
    if (command == 0x10 || command == 0x91) {
        d->error = 0;
        d->status = IDE_READY | IDE_SEEK;
        ide_set_irq(m);
        return;
    }
    ide_abort(m);
}

static void ide_sector_done(struct machine *m)
{
    struct ide_state *d = &m->ide;
    d->data_pos = 0;
    d->lba++;
    if (d->remaining)
        d->remaining--;
    if (d->remaining) {
        if ((uint64_t)d->lba * IDE_SECTOR_LEN >= d->disk_size) {
            ide_abort(m);
            return;
        }
        d->status = IDE_READY | IDE_SEEK | IDE_DRQ;
        ide_set_irq(m);
    } else {
        d->status = IDE_READY | IDE_SEEK;
        if (d->writing)
            ide_set_irq(m);
    }
}

uint32_t ide_data_read(struct machine *m, unsigned size)
{
    struct ide_state *d = &m->ide;
    uint32_t value = 0;
    unsigned i;
    if (d->writing || !(d->status & IDE_DRQ) || !d->remaining)
        return 0;
    for (i = 0; i < size; i++) {
        size_t at = (size_t)d->lba * IDE_SECTOR_LEN + d->data_pos;
        value |= (uint32_t)d->disk[at] << (i * 8);
        d->data_pos++;
        if (d->data_pos == IDE_SECTOR_LEN) {
            ide_sector_done(m);
            break;
        }
    }
    return value;
}

void ide_data_write(struct machine *m, uint32_t value, unsigned size)
{
    struct ide_state *d = &m->ide;
    unsigned i;
    if (!d->writing || !(d->status & IDE_DRQ) || !d->remaining)
        return;
    for (i = 0; i < size; i++) {
        size_t at = (size_t)d->lba * IDE_SECTOR_LEN + d->data_pos;
        d->disk[at] = (uint8_t)(value >> (i * 8));
        d->data_pos++;
        if (d->data_pos == IDE_SECTOR_LEN) {
            ide_sector_done(m);
            break;
        }
    }
}

void ide_control(struct machine *m, uint8_t value)
{
    struct ide_state *d = &m->ide;
    uint8_t old = d->control;
    d->control = value;
    if (value & 2)
        irq_level(m, 14, 0);
    if ((value & 4) && !(old & 4)) {
        ide_clear_irq(m);
        d->status = IDE_BUSY;
        d->remaining = d->data_pos = 0;
    } else if (!(value & 4) && (old & 4)) {
        d->error = 1;
        d->status = IDE_READY | IDE_SEEK;
    }
    if (!(value & 2) && (old & 2) && d->irq_pending)
        irq_level(m, 14, 1);
}
