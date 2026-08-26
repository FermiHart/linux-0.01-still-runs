#include <linux/kvm.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>

#include "../../bemu/kvm.h"
#include "../../bemu/machine.h"
#include "../../bemu/memory.h"

struct fixture {
    struct machine machine;
};

static int failures;

static void check(int condition, const char *name)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", name);
        failures++;
    } else {
        printf("ok  %s\n", name);
    }
}

static void must_ioctl(int fd, unsigned long request, void *argument,
                       const char *name)
{
    if (ioctl(fd, request, argument) < 0) {
        perror(name);
        exit(1);
    }
}

static void setup(struct fixture *f)
{
    struct kvm_guest_debug debug;
    enum bemu_memory_status memory_status;

    memset(f, 0, sizeof *f);
    machine_create(&f->machine);
    memory_status = bemu_memory_map_ram(&f->machine, RAM_SIZE, NULL, NULL);
    check(memory_status == BEMU_MEMORY_OK, "KVM test RAM maps");
    if (memory_status != BEMU_MEMORY_OK)
        exit(1);
    f->machine.ram[0] = 0x90; /* nop */
    setup_kvm(&f->machine);
    memset(&debug, 0, sizeof debug);
    debug.control = KVM_GUESTDBG_ENABLE | KVM_GUESTDBG_SINGLESTEP;
    must_ioctl(f->machine.vcpu, KVM_SET_GUEST_DEBUG, &debug,
               "KVM_SET_GUEST_DEBUG");
}

static void cleanup(struct fixture *f)
{
    machine_destroy(&f->machine);
}

static void get_pic(struct fixture *f, uint32_t chip_id,
                    struct kvm_irqchip *chip, const char *name)
{
    memset(chip, 0, sizeof *chip);
    chip->chip_id = chip_id;
    must_ioctl(f->machine.vm, KVM_GET_IRQCHIP, chip, name);
}

static void set_pic(struct fixture *f, struct kvm_irqchip *chip,
                    const char *name)
{
    must_ioctl(f->machine.vm, KVM_SET_IRQCHIP, chip, name);
}

static void clear_pic_irq(struct fixture *f, uint32_t chip_id, unsigned irq,
                          const char *get_name, const char *set_name)
{
    struct kvm_irqchip chip;
    uint8_t mask = (uint8_t)(1u << irq);

    get_pic(f, chip_id, &chip, get_name);
    chip.chip.pic.irr &= (uint8_t)~mask;
    chip.chip.pic.isr &= (uint8_t)~mask;
    chip.chip.pic.last_irr &= (uint8_t)~mask;
    set_pic(f, &chip, set_name);
}

static int pic_irq_pending(struct fixture *f, uint32_t chip_id, unsigned irq,
                           const char *name)
{
    struct kvm_irqchip chip;
    uint8_t mask = (uint8_t)(1u << irq);

    get_pic(f, chip_id, &chip, name);
    return ((chip.chip.pic.irr | chip.chip.pic.isr) & mask) != 0;
}

static void set_master_irq_pending(struct fixture *f, unsigned irq)
{
    struct kvm_irqchip chip;
    uint8_t mask = (uint8_t)(1u << irq);

    get_pic(f, KVM_IRQCHIP_PIC_MASTER, &chip, "KVM_GET_IRQCHIP master");
    chip.chip.pic.irr |= mask;
    set_pic(f, &chip, "KVM_SET_IRQCHIP master pending");
}

static void run_step_once(struct fixture *f)
{
    struct kvm_mp_state mp;
    struct kvm_regs regs;

    memset(&mp, 0, sizeof mp);
    mp.mp_state = KVM_MP_STATE_RUNNABLE;
    must_ioctl(f->machine.vcpu, KVM_SET_MP_STATE, &mp, "KVM_SET_MP_STATE");
    memset(&regs, 0, sizeof regs);
    regs.rip = 0;
    regs.rflags = 2;
    must_ioctl(f->machine.vcpu, KVM_SET_REGS, &regs, "KVM_SET_REGS");
    if (ioctl(f->machine.vcpu, KVM_RUN, 0) < 0) {
        perror("KVM_RUN");
        exit(1);
    }
    if (f->machine.run->exit_reason != KVM_EXIT_DEBUG) {
        fprintf(stderr, "unexpected KVM exit reason: %u",
                f->machine.run->exit_reason);
        if (f->machine.run->exit_reason == KVM_EXIT_INTERNAL_ERROR)
            fprintf(stderr, " suberror=%u",
                    f->machine.run->internal.suberror);
        fputc('\n', stderr);
    }
    check(f->machine.run->exit_reason == KVM_EXIT_DEBUG,
          "minimal vCPU completes one single-step run");
    irq_run_completed(&f->machine);
}

static void test_drop_reaches_kvm_boundary(void)
{
    struct fixture f;
    struct kvm_irqchip chip;

    setup(&f);
    check(irq_inject_fault(&f.machine, BEMU_IRQ_FAULT_DROP_ONCE, 0) == 0,
          "KVM drop fault arms");
    irq_pulse(&f.machine, 0);
    get_pic(&f, KVM_IRQCHIP_PIC_MASTER, &chip,
            "KVM_GET_IRQCHIP master");
    check((chip.chip.pic.irr & 0x01) == 0,
          "dropped IRQ0 never reaches KVM IRR");
    irq_pulse(&f.machine, 0);
    get_pic(&f, KVM_IRQCHIP_PIC_MASTER, &chip,
            "KVM_GET_IRQCHIP master");
    check((chip.chip.pic.irr & 0x01) != 0,
          "next IRQ0 reaches KVM after one-shot drop");
    cleanup(&f);
}

static void test_duplicate_crosses_completed_runs(void)
{
    struct fixture f;
    struct kvm_irqchip chip;

    setup(&f);
    check(irq_inject_fault(&f.machine, BEMU_IRQ_FAULT_DUPLICATE_ONCE, 0) == 0,
          "KVM duplicate fault arms");
    irq_pulse(&f.machine, 0);
    get_pic(&f, KVM_IRQCHIP_PIC_MASTER, &chip,
            "KVM_GET_IRQCHIP master");
    check((chip.chip.pic.irr & 0x01) != 0,
          "original duplicate edge reaches KVM IRR");

    run_step_once(&f);
    get_pic(&f, KVM_IRQCHIP_PIC_MASTER, &chip,
            "KVM_GET_IRQCHIP master");
    check((chip.chip.pic.irr & 0x01) != 0,
          "pending KVM IRR defers duplicate replay");

    clear_pic_irq(&f, KVM_IRQCHIP_PIC_MASTER, 0,
                  "KVM_GET_IRQCHIP master", "KVM_SET_IRQCHIP master");
    check(!pic_irq_pending(&f, KVM_IRQCHIP_PIC_MASTER, 0,
                           "KVM_GET_IRQCHIP master"),
          "master PIC is clear before duplicate replay");
    run_step_once(&f);
    get_pic(&f, KVM_IRQCHIP_PIC_MASTER, &chip,
            "KVM_GET_IRQCHIP master");
    check((chip.chip.pic.irr & 0x01) != 0,
          "quiescent PIC receives duplicate after completed run");

    clear_pic_irq(&f, KVM_IRQCHIP_PIC_MASTER, 0,
                  "KVM_GET_IRQCHIP master", "KVM_SET_IRQCHIP master");
    check(!pic_irq_pending(&f, KVM_IRQCHIP_PIC_MASTER, 0,
                           "KVM_GET_IRQCHIP master"),
          "master PIC is clear before one-shot check");
    run_step_once(&f);
    get_pic(&f, KVM_IRQCHIP_PIC_MASTER, &chip,
            "KVM_GET_IRQCHIP master");
    check((chip.chip.pic.irr & 0x01) == 0,
          "later completed run does not emit third edge");
    cleanup(&f);
}

static void test_slave_duplicate_waits_for_cascade(void)
{
    struct fixture f;

    setup(&f);
    check(irq_inject_fault(&f.machine, BEMU_IRQ_FAULT_DUPLICATE_ONCE, 14) == 0,
          "KVM slave duplicate fault arms");
    irq_pulse(&f.machine, 14);
    check(pic_irq_pending(&f, KVM_IRQCHIP_PIC_SLAVE, 6,
                          "KVM_GET_IRQCHIP slave"),
          "original IRQ14 reaches slave IRR");
    check(pic_irq_pending(&f, KVM_IRQCHIP_PIC_MASTER, 2,
                          "KVM_GET_IRQCHIP master"),
          "original IRQ14 raises master cascade");

    clear_pic_irq(&f, KVM_IRQCHIP_PIC_SLAVE, 6,
                  "KVM_GET_IRQCHIP slave", "KVM_SET_IRQCHIP slave");
    set_master_irq_pending(&f, 2);
    check(!pic_irq_pending(&f, KVM_IRQCHIP_PIC_SLAVE, 6,
                           "KVM_GET_IRQCHIP slave") &&
          pic_irq_pending(&f, KVM_IRQCHIP_PIC_MASTER, 2,
                          "KVM_GET_IRQCHIP master"),
          "only master cascade remains pending");
    run_step_once(&f);
    check(!pic_irq_pending(&f, KVM_IRQCHIP_PIC_SLAVE, 6,
                           "KVM_GET_IRQCHIP slave"),
          "master cascade alone defers slave replay");

    clear_pic_irq(&f, KVM_IRQCHIP_PIC_MASTER, 2,
                  "KVM_GET_IRQCHIP master", "KVM_SET_IRQCHIP master");
    check(!pic_irq_pending(&f, KVM_IRQCHIP_PIC_MASTER, 2,
                           "KVM_GET_IRQCHIP master") &&
          !pic_irq_pending(&f, KVM_IRQCHIP_PIC_SLAVE, 6,
                           "KVM_GET_IRQCHIP slave"),
          "slave and cascade are clear before replay");
    run_step_once(&f);
    check(pic_irq_pending(&f, KVM_IRQCHIP_PIC_SLAVE, 6,
                          "KVM_GET_IRQCHIP slave"),
          "quiescent cascade receives duplicate IRQ14");

    clear_pic_irq(&f, KVM_IRQCHIP_PIC_SLAVE, 6,
                  "KVM_GET_IRQCHIP slave", "KVM_SET_IRQCHIP slave");
    clear_pic_irq(&f, KVM_IRQCHIP_PIC_MASTER, 2,
                  "KVM_GET_IRQCHIP master", "KVM_SET_IRQCHIP master");
    run_step_once(&f);
    check(!pic_irq_pending(&f, KVM_IRQCHIP_PIC_SLAVE, 6,
                           "KVM_GET_IRQCHIP slave"),
          "later run does not emit third slave edge");
    cleanup(&f);
}

int main(void)
{
    test_drop_reaches_kvm_boundary();
    test_duplicate_crosses_completed_runs();
    test_slave_duplicate_waits_for_cascade();
    if (failures) {
        fprintf(stderr, "\n%d test(s) failed\n", failures);
        return 1;
    }
    printf("\nall KVM IRQ fault-injection tests passed\n");
    return 0;
}
