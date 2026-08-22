#ifndef BEMU_IDE_H
#define BEMU_IDE_H

#include <stdint.h>
#include <stddef.h>

#define IDE_HEADS      5
#define IDE_SECTORS    17
#define IDE_CYLINDERS  977
#define IDE_SECTOR_LEN 512

#define IDE_DATA       0x1F0
#define IDE_ERROR      0x1F1
#define IDE_NSECTOR    0x1F2
#define IDE_SECTOR     0x1F3
#define IDE_LCYL       0x1F4
#define IDE_HCYL       0x1F5
#define IDE_CURRENT    0x1F6
#define IDE_STATUS     0x1F7
#define IDE_CONTROL    0x3F6

#define IDE_ERR        0x01
#define IDE_DRQ        0x08
#define IDE_SEEK       0x10
#define IDE_READY      0x40
#define IDE_BUSY       0x80

struct machine;

struct ide_state {
    uint8_t *disk;
    size_t disk_size;
    uint8_t error, count, sector, lcyl, hcyl, current, status, control;
    uint32_t lba;
    unsigned remaining, data_pos;
    int writing, irq_pending;
};

void ide_reset(struct ide_state *ide);
void map_disk(struct ide_state *ide, const char *path);
void ide_command(struct machine *m, uint8_t command);
uint32_t ide_data_read(struct machine *m, unsigned size);
void ide_data_write(struct machine *m, uint32_t value, unsigned size);
void ide_control(struct machine *m, uint8_t value);
void ide_clear_irq(struct machine *m);

#endif
