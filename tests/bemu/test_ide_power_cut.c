/* Deterministic power cuts at semantic boundaries in production IDE writes. */

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../../bemu/ide.h"
#include "../../bemu/machine.h"

static int failures;
static int irq14_level;
static unsigned irq14_raises;

void die(const char *what)
{
    perror(what);
    exit(2);
}

void fail(const char *what)
{
    fprintf(stderr, "FAIL: production failure: %s\n", what);
    exit(2);
}

void irq_level(struct machine *m, unsigned irq, int level)
{
    (void)m;
    if (irq != 14)
        return;
    if (level && !irq14_level)
        irq14_raises++;
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
    memset(disk, 0x11, disk_size);
    m->ide.disk = disk;
    m->ide.disk_size = disk_size;
    ide_reset(&m->ide);
    irq14_level = 0;
    irq14_raises = 0;
}

static void set_chs(struct ide_state *ide, uint32_t lba, uint8_t count)
{
    uint32_t cylinder = lba / (IDE_HEADS * IDE_SECTORS);
    uint32_t within = lba % (IDE_HEADS * IDE_SECTORS);

    ide->count = count;
    ide->sector = (uint8_t)(within % IDE_SECTORS + 1);
    ide->current = (uint8_t)(0xa0 | (within / IDE_SECTORS));
    ide->lcyl = (uint8_t)cylinder;
    ide->hcyl = (uint8_t)(cylinder >> 8);
}

static void write_payload(struct machine *m, const uint8_t *payload,
                          unsigned sectors)
{
    unsigned sector;
    unsigned word;

    for (sector = 0; sector < sectors && !m->ide.powered_off; sector++) {
        for (word = 0; word < IDE_SECTOR_LEN / 2; word++) {
            size_t at = (size_t)sector * IDE_SECTOR_LEN + word * 2;
            uint32_t value = payload[at] | ((uint32_t)payload[at + 1] << 8);
            ide_data_write(m, value, 2);
            if (m->ide.powered_off)
                break;
        }
        if (!m->ide.powered_off && m->ide.remaining && m->ide.irq_pending)
            ide_clear_irq(m);
    }
}

static int sector_is(const uint8_t *disk, unsigned sector, uint8_t value)
{
    unsigned i;

    for (i = 0; i < IDE_SECTOR_LEN; i++)
        if (disk[(size_t)sector * IDE_SECTOR_LEN + i] != value)
            return 0;
    return 1;
}

struct cut_case {
    const char *name;
    enum ide_power_cut_boundary boundary;
    uint32_t cut_lba;
    unsigned committed_sectors;
    unsigned irq_raises;
};

static void test_boundary_matrix(void)
{
    static const struct cut_case cases[] = {
        {"write accepted at first sector", IDE_POWER_CUT_WRITE_ACCEPTED, 0, 0, 0},
        {"first payload received", IDE_POWER_CUT_PAYLOAD_RECEIVED, 0, 0, 0},
        {"first sector committed", IDE_POWER_CUT_SECTOR_COMMITTED, 0, 1, 0},
        {"first completion IRQ requested", IDE_POWER_CUT_IRQ_REQUESTED, 0, 1, 1},
        {"second sector accepted", IDE_POWER_CUT_WRITE_ACCEPTED, 1, 1, 0},
        {"second payload received", IDE_POWER_CUT_PAYLOAD_RECEIVED, 1, 1, 1},
        {"second sector committed", IDE_POWER_CUT_SECTOR_COMMITTED, 1, 2, 1},
        {"second completion IRQ requested", IDE_POWER_CUT_IRQ_REQUESTED, 1, 2, 2},
    };
    uint8_t payload[2 * IDE_SECTOR_LEN];
    size_t i;

    memset(payload, 0xa5, IDE_SECTOR_LEN);
    memset(payload + IDE_SECTOR_LEN, 0x5a, IDE_SECTOR_LEN);
    for (i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        struct machine m;
        uint8_t disk[2 * IDE_SECTOR_LEN];
        char assertion[160];

        setup_ide(&m, disk, sizeof disk);
        set_chs(&m.ide, 0, 2);
        if (ide_arm_power_cut(&m.ide, cases[i].boundary,
                              cases[i].cut_lba) < 0) {
            check(0, "power-cut matrix arms");
            continue;
        }
        ide_command(&m, 0x30);
        write_payload(&m, payload, 2);
        snprintf(assertion, sizeof assertion, "%s has exact media prefix",
                 cases[i].name);
        check(sector_is(disk, 0, cases[i].committed_sectors > 0 ? 0xa5 : 0x11) &&
              sector_is(disk, 1, cases[i].committed_sectors > 1 ? 0x5a : 0x11),
              assertion);
        snprintf(assertion, sizeof assertion, "%s has exact IRQ history",
                 cases[i].name);
        check(irq14_raises == cases[i].irq_raises, assertion);
        snprintf(assertion, sizeof assertion, "%s powers off once and clears transfer",
                 cases[i].name);
        check(m.ide.power_cut_triggered && m.ide.powered_off &&
              !m.ide.power_cut_armed && !m.ide.remaining &&
              !m.ide.data_pos && !m.ide.writing && !m.ide.irq_pending &&
              m.ide.status == 0, assertion);
    }
}

static void test_partial_sector_and_reset(void)
{
    struct machine m;
    uint8_t disk[2 * IDE_SECTOR_LEN];
    uint8_t payload[2 * IDE_SECTOR_LEN];
    unsigned i;

    setup_ide(&m, disk, sizeof disk);
    set_chs(&m.ide, 0, 1);
    ide_command(&m, 0x30);
    for (i = 0; i < IDE_SECTOR_LEN / 4; i++)
        ide_data_write(&m, 0xaaaaaaaa, 2);
    ide_power_off(&m);
    check(sector_is(disk, 0, 0x11),
          "manual cut discards a partially received sector");
    check(!irq14_raises && m.ide.powered_off && !m.ide.remaining,
          "manual cut is terminal and raises no completion IRQ");
    ide_command(&m, 0x30);
    ide_data_write(&m, 0xffffffff, 4);
    ide_control(&m, 4);
    check(sector_is(disk, 0, 0x11) && m.ide.status == 0 &&
          !m.ide.remaining && m.ide.powered_off,
          "powered-off device ignores later command/data/control PIO");

    memset(payload, 0xa5, IDE_SECTOR_LEN);
    memset(payload + IDE_SECTOR_LEN, 0x5a, IDE_SECTOR_LEN);
    ide_reset(&m.ide);
    set_chs(&m.ide, 0, 2);
    ide_command(&m, 0x30);
    write_payload(&m, payload, 2);
    check(sector_is(disk, 0, 0xa5) && sector_is(disk, 1, 0x5a),
          "reset restores normal atomic sector writes after a cut");
    check(!m.ide.powered_off && !m.ide.power_cut_triggered &&
          !m.ide.remaining && irq14_raises == 2,
          "normal write completes both IRQ boundaries after reset");
}

static void test_arming_contract(void)
{
    struct machine m;
    uint8_t disk[2 * IDE_SECTOR_LEN];

    setup_ide(&m, disk, sizeof disk);
    check(ide_arm_power_cut(&m.ide, IDE_POWER_CUT_NONE, 0) < 0,
          "none is not an armable power-cut boundary");
    check(ide_arm_power_cut(&m.ide, IDE_POWER_CUT_PAYLOAD_RECEIVED, 2) < 0,
          "power cut outside media is rejected");
    check(ide_arm_power_cut(&m.ide, IDE_POWER_CUT_PAYLOAD_RECEIVED, 1) == 0,
          "valid LBA-selected power cut arms");
    check(ide_arm_power_cut(&m.ide, IDE_POWER_CUT_IRQ_REQUESTED, 0) < 0,
          "second simultaneous power cut is rejected");
    set_chs(&m.ide, 0, 1);
    ide_command(&m, 0x30);
    check(m.ide.power_cut_armed && !m.ide.power_cut_triggered,
          "unrelated LBA does not consume an armed cut");
}

static void test_irq_request_boundary(void)
{
    struct machine m;
    uint8_t disk[2 * IDE_SECTOR_LEN];
    uint8_t payload[2 * IDE_SECTOR_LEN];

    memset(payload, 0xa5, sizeof payload);
    setup_ide(&m, disk, sizeof disk);
    m.ide.control = 2;
    set_chs(&m.ide, 0, 1);
    check(ide_arm_power_cut(&m.ide, IDE_POWER_CUT_IRQ_REQUESTED, 0) == 0,
          "masked completion-IRQ cut arms");
    ide_command(&m, 0x30);
    write_payload(&m, payload, 1);
    check(!m.ide.power_cut_triggered && !m.ide.powered_off &&
          m.ide.power_cut_armed && !irq14_raises && sector_is(disk, 0, 0xa5),
          "masked completion does not trigger IRQ-request boundary");

    setup_ide(&m, disk, sizeof disk);
    set_chs(&m.ide, 0, 2);
    ide_inject_fault(&m.ide, IDE_FAULT_WRITE, 1);
    check(ide_arm_power_cut(&m.ide, IDE_POWER_CUT_IRQ_REQUESTED, 0) == 0,
          "error-path completion-IRQ cut arms");
    ide_command(&m, 0x30);
    write_payload(&m, payload, 1);
    check(!m.ide.power_cut_triggered && !m.ide.powered_off &&
          m.ide.power_cut_armed && (m.ide.status & IDE_ERR) &&
          irq14_raises == 1 && sector_is(disk, 0, 0xa5),
          "next-sector abort IRQ is not a completion-IRQ request");
}

static enum ide_power_cut_boundary parse_boundary(const char *name)
{
    if (strcmp(name, "none") == 0)
        return IDE_POWER_CUT_NONE;
    if (strcmp(name, "accepted") == 0)
        return IDE_POWER_CUT_WRITE_ACCEPTED;
    if (strcmp(name, "payload") == 0)
        return IDE_POWER_CUT_PAYLOAD_RECEIVED;
    if (strcmp(name, "committed") == 0)
        return IDE_POWER_CUT_SECTOR_COMMITTED;
    if (strcmp(name, "irq") == 0)
        return IDE_POWER_CUT_IRQ_REQUESTED;
    return (enum ide_power_cut_boundary)-1;
}

static uint32_t parse_lba(const char *text)
{
    char *end;
    unsigned long value;

    errno = 0;
    value = strtoul(text, &end, 0);
    if (errno || *text == '\0' || *end != '\0' || value > UINT32_MAX)
        fail("invalid test LBA");
    return (uint32_t)value;
}

static int drive_image(const char *path, uint32_t start_lba,
                       enum ide_power_cut_boundary boundary, uint32_t cut_lba)
{
    struct machine m;
    uint8_t payload[2 * IDE_SECTOR_LEN];
    size_t at;
    unsigned i;

    memset(&m, 0, sizeof m);
    map_disk(&m.ide, path);
    if ((uint64_t)start_lba + 2 > m.ide.disk_size / IDE_SECTOR_LEN)
        fail("test write exceeds IDE image");
    at = (size_t)start_lba * IDE_SECTOR_LEN;
    for (i = 0; i < sizeof payload; i++)
        payload[i] = m.ide.disk[at + i] ^ 0xa5;
    set_chs(&m.ide, start_lba, 2);
    irq14_level = 0;
    irq14_raises = 0;
    if (boundary != IDE_POWER_CUT_NONE &&
        ide_arm_power_cut(&m.ide, boundary, cut_lba) < 0)
        fail("could not arm test power cut");
    ide_command(&m, 0x30);
    write_payload(&m, payload, 2);
    if (ide_sync_disk(&m.ide) < 0)
        die("msync test image");
    printf("triggered=%d powered_off=%d irq_raises=%u remaining=%u\n",
           m.ide.power_cut_triggered, m.ide.powered_off, irq14_raises,
           m.ide.remaining);
    if (ide_unmap_disk(&m.ide) < 0)
        die("unmap test image");
    return 0;
}

int main(int argc, char **argv)
{
    if (argc == 6 && strcmp(argv[1], "--drive") == 0) {
        enum ide_power_cut_boundary boundary = parse_boundary(argv[4]);
        if ((int)boundary < 0)
            fail("invalid power-cut boundary");
        return drive_image(argv[2], parse_lba(argv[3]), boundary,
                           parse_lba(argv[5]));
    }
    if (argc != 1) {
        fprintf(stderr, "usage: %s [--drive IMAGE START_LBA CUT CUT_LBA]\n",
                argv[0]);
        return 2;
    }
    test_boundary_matrix();
    test_partial_sector_and_reset();
    test_arming_contract();
    test_irq_request_boundary();
    if (failures) {
        fprintf(stderr, "\n%d IDE power-cut test(s) failed\n", failures);
        return 1;
    }
    printf("\nall deterministic IDE power-cut tests passed\n");
    return 0;
}
