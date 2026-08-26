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

enum ide_fault_kind {
    IDE_FAULT_NONE,
    IDE_FAULT_READ,
    IDE_FAULT_WRITE,
};

enum ide_power_cut_boundary {
    IDE_POWER_CUT_NONE,
    IDE_POWER_CUT_WRITE_ACCEPTED,
    IDE_POWER_CUT_PAYLOAD_RECEIVED,
    IDE_POWER_CUT_SECTOR_COMMITTED,
    IDE_POWER_CUT_IRQ_REQUESTED,
};

struct ide_state {
    uint8_t *disk;
    size_t disk_size;
    uint8_t error, count, sector, lcyl, hcyl, current, status, control;
    uint32_t lba;
    uint32_t fault_lba;
    uint32_t power_cut_lba;
    unsigned remaining, data_pos;
    int writing, irq_pending, disk_mapped;
    int power_cut_armed, power_cut_triggered, powered_off;
    enum ide_fault_kind fault_kind;
    enum ide_power_cut_boundary power_cut_boundary;
    uint8_t write_buffer[IDE_SECTOR_LEN];
};

void ide_reset(struct ide_state *ide);
void ide_inject_fault(struct ide_state *ide, enum ide_fault_kind kind,
                      uint32_t lba);
int ide_arm_power_cut(struct ide_state *ide,
                      enum ide_power_cut_boundary boundary, uint32_t lba);
void ide_power_off(struct machine *m);
int ide_sync_disk(struct ide_state *ide);
int ide_unmap_disk(struct ide_state *ide);
void map_disk(struct ide_state *ide, const char *path);
int ide_experience_matches(const struct ide_state *ide, const char *experience);
void ide_command(struct machine *m, uint8_t command);
uint32_t ide_data_read(struct machine *m, unsigned size);
void ide_data_write(struct machine *m, uint32_t value, unsigned size);
void ide_control(struct machine *m, uint8_t value);
void ide_clear_irq(struct machine *m);

#endif
