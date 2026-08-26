#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../bemu/ide.h"
#include "../../bemu/machine.h"

static int failures;
static int irq14_level;

void die(const char *what)
{
    fprintf(stderr, "FAIL: unexpected production error: %s\n", what);
    abort();
}

void fail(const char *what)
{
    fprintf(stderr, "FAIL: unexpected production failure: %s\n", what);
    abort();
}

void irq_level(struct machine *m, unsigned irq, int level)
{
    (void)m;
    if (irq == 14)
        irq14_level = level;
}

static void check(int condition, const char *name)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", name);
        failures++;
    } else {
        printf("ok  %s\n", name);
    }
}

static void setup_ide(struct machine *m, uint8_t *disk, size_t disk_size)
{
    memset(m, 0, sizeof *m);
    memset(disk, 0, disk_size);
    m->ide.disk = disk;
    m->ide.disk_size = disk_size;
    ide_reset(&m->ide);
    irq14_level = 0;
}

static void test_read_fault(void)
{
    struct machine m;
    uint8_t disk[2 * IDE_SECTOR_LEN];

    setup_ide(&m, disk, sizeof disk);
    disk[0] = 0x5a;
    ide_inject_fault(&m.ide, IDE_FAULT_READ, 0);
    ide_command(&m, 0x20);
    check((m.ide.status & (IDE_ERR | IDE_DRQ)) == IDE_ERR,
          "read fault reports ERR without DRQ");
    check(m.ide.error == 4 && m.ide.remaining == 0,
          "read fault reports ATA abort state");
    check(m.ide.irq_pending && irq14_level,
          "read fault raises IRQ14");
    check(ide_data_read(&m, 1) == 0 && disk[0] == 0x5a,
          "read fault transfers no disk data");

    ide_command(&m, 0x20);
    check((m.ide.status & (IDE_ERR | IDE_DRQ)) == IDE_DRQ,
          "read fault is consumed once");
    check(ide_data_read(&m, 1) == 0x5a,
          "read succeeds after injected fault");
}

static void test_write_fault(void)
{
    struct machine m;
    uint8_t disk[2 * IDE_SECTOR_LEN];
    unsigned i;

    setup_ide(&m, disk, sizeof disk);
    disk[0] = 0x33;
    ide_inject_fault(&m.ide, IDE_FAULT_WRITE, 0);
    ide_command(&m, 0x30);
    check((m.ide.status & (IDE_ERR | IDE_DRQ)) == IDE_ERR,
          "write fault reports ERR without DRQ");
    check(m.ide.error == 4 && m.ide.remaining == 0,
          "write fault reports ATA abort state");
    check(m.ide.irq_pending && irq14_level,
          "write fault raises IRQ14");
    ide_data_write(&m, 0xaa, 1);
    check(disk[0] == 0x33, "write fault leaves sector unchanged");

    ide_command(&m, 0x30);
    check((m.ide.status & (IDE_ERR | IDE_DRQ)) == IDE_DRQ,
          "write fault is consumed once");
    for (i = 0; i < IDE_SECTOR_LEN / 4; i++)
        ide_data_write(&m, 0xaaaaaaaa, 4);
    check(disk[0] == 0xaa && disk[IDE_SECTOR_LEN - 1] == 0xaa,
          "complete sector write succeeds after injected fault");
}

static void test_fault_scope(void)
{
    struct machine m;
    uint8_t disk[2 * IDE_SECTOR_LEN];

    setup_ide(&m, disk, sizeof disk);
    ide_inject_fault(&m.ide, IDE_FAULT_READ, 0);
    ide_command(&m, 0x30);
    check((m.ide.status & IDE_DRQ) != 0,
          "read fault does not affect write command");
    ide_command(&m, 0x20);
    check((m.ide.status & IDE_ERR) != 0,
          "operation-mismatched fault remains armed");

    ide_inject_fault(&m.ide, IDE_FAULT_READ, 1);
    ide_command(&m, 0x20);
    check((m.ide.status & IDE_DRQ) != 0,
          "fault for another LBA does not affect command");
    m.ide.sector = 2;
    ide_command(&m, 0x20);
    check((m.ide.status & IDE_ERR) != 0,
          "fault triggers on its selected LBA");
}

static void test_multisector_fault(void)
{
    struct machine m;
    uint8_t disk[2 * IDE_SECTOR_LEN];
    unsigned i;

    setup_ide(&m, disk, sizeof disk);
    m.ide.count = 2;
    ide_inject_fault(&m.ide, IDE_FAULT_READ, 1);
    ide_command(&m, 0x20);
    for (i = 0; i < IDE_SECTOR_LEN / 4; i++)
        (void)ide_data_read(&m, 4);
    check((m.ide.status & (IDE_ERR | IDE_DRQ)) == IDE_ERR,
          "read fault triggers on later sector of one command");
    check(m.ide.lba == 1 && m.ide.remaining == 0,
          "later read fault stops multiblock transfer");

    setup_ide(&m, disk, sizeof disk);
    m.ide.count = 2;
    ide_inject_fault(&m.ide, IDE_FAULT_WRITE, 1);
    ide_command(&m, 0x30);
    for (i = 0; i < IDE_SECTOR_LEN / 4; i++)
        ide_data_write(&m, 0xaaaaaaaa, 4);
    check((m.ide.status & (IDE_ERR | IDE_DRQ)) == IDE_ERR,
          "write fault triggers on later sector of one command");
    check(disk[0] == 0xaa && disk[IDE_SECTOR_LEN] == 0,
          "later write fault preserves failing sector");
}

int main(void)
{
    test_read_fault();
    test_write_fault();
    test_fault_scope();
    test_multisector_fault();
    if (failures) {
        fprintf(stderr, "\n%d test(s) failed\n", failures);
        return 1;
    }
    printf("\nall IDE fault-injection tests passed\n");
    return 0;
}
