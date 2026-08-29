/*
 * Maintainer and adaptation: F E R M I INFINITY H A R T <contact@fermihart.com>
 * bEMU-NANO provenance: see bemu/README.md
 */

#include "kvm.h"
#include "machine.h"

#include <errno.h>
#include <fcntl.h>
#include <linux/kvm.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>

static const uint8_t bootstrap_gdt[24] = {
    0,0,0,0,0,0,0,0,
    0xff,0xff,0,0,0,0x9a,0xcf,0,
    0xff,0xff,0,0,0,0x92,0xcf,0,
};

static void set_segment(struct kvm_segment *s, uint16_t selector, int code)
{
    memset(s, 0, sizeof *s);
    s->base = 0;
    s->limit = 0xffffffff;
    s->selector = selector;
    s->type = code ? 0xb : 3;
    s->present = 1;
    s->s = 1;
    s->g = 1;
    s->db = 1;
}

void setup_kvm(struct machine *m)
{
    struct kvm_userspace_memory_region region;
    struct kvm_cpuid2 *cpuid;
    struct kvm_sregs sregs;
    struct kvm_regs regs;
    uint64_t identity = 0xfffbc000ULL;
    int kvm, mmap_size;

    _Static_assert(KERNEL_MAX <= GDT_GPA, "kernel limit overlaps bootstrap GDT");
    if (!m->ram || m->ram_size != RAM_SIZE)
        fail("guest RAM is not prepared");

    kvm = open("/dev/kvm", O_RDWR);
    if (kvm < 0) die("/dev/kvm");
    if (ioctl(kvm, KVM_GET_API_VERSION, 0) != KVM_API_VERSION)
        fail("KVM API version mismatch");
    if (ioctl(kvm, KVM_CHECK_EXTENSION, KVM_CAP_IRQCHIP) <= 0)
        fail("KVM irqchip support is required");
    if (ioctl(kvm, KVM_CHECK_EXTENSION, KVM_CAP_MP_STATE) <= 0)
        fail("KVM MP state support is required");
    m->vm = ioctl(kvm, KVM_CREATE_VM, 0);
    if (m->vm < 0) die("KVM_CREATE_VM");
    if (ioctl(m->vm, KVM_SET_TSS_ADDR, 0xfffbd000UL) < 0)
        die("KVM_SET_TSS_ADDR");
    if (ioctl(m->vm, KVM_SET_IDENTITY_MAP_ADDR, &identity) < 0)
        die("KVM_SET_IDENTITY_MAP_ADDR");
    memset(&region, 0, sizeof region);
    region.slot = 0;
    region.guest_phys_addr = 0;
    region.memory_size = m->ram_size;
    region.userspace_addr = (uint64_t)m->ram;
    if (ioctl(m->vm, KVM_SET_USER_MEMORY_REGION, &region) < 0)
        die("KVM_SET_USER_MEMORY_REGION");
    memcpy(m->ram + GDT_GPA, bootstrap_gdt, sizeof bootstrap_gdt);
    if (ioctl(m->vm, KVM_CREATE_IRQCHIP, 0) < 0)
        die("KVM_CREATE_IRQCHIP");
    m->vcpu = ioctl(m->vm, KVM_CREATE_VCPU, 0);
    if (m->vcpu < 0) die("KVM_CREATE_VCPU");

    {
        uint32_t nent = 128;
        for (;;) {
            size_t bytes, entry_bytes;
            uint32_t needed;
            int error;

            if (__builtin_mul_overflow((size_t)nent, sizeof(cpuid->entries[0]),
                                       &entry_bytes) ||
                __builtin_add_overflow(sizeof(*cpuid), entry_bytes, &bytes))
                fail("KVM CPUID entry count is too large");
            cpuid = calloc(1, bytes);
            if (!cpuid)
                die("calloc CPUID");
            cpuid->nent = nent;
            if (ioctl(kvm, KVM_GET_SUPPORTED_CPUID, cpuid) == 0)
                break;
            error = errno;
            needed = cpuid->nent;
            free(cpuid);
            if (error != E2BIG) {
                errno = error;
                die("KVM_GET_SUPPORTED_CPUID");
            }
            if (needed <= nent) {
                if (nent > UINT32_MAX / 2)
                    fail("KVM CPUID entry count overflow");
                needed = nent * 2;
            }
            nent = needed;
        }
    }
    if (ioctl(m->vcpu, KVM_SET_CPUID2, cpuid) < 0)
        die("KVM_SET_CPUID2");
    free(cpuid);
    mmap_size = ioctl(kvm, KVM_GET_VCPU_MMAP_SIZE, 0);
    close(kvm);
    if (mmap_size <= 0) die("KVM_GET_VCPU_MMAP_SIZE");
    m->run_size = (size_t)mmap_size;
    m->run = mmap(NULL, m->run_size, PROT_READ | PROT_WRITE,
                  MAP_SHARED, m->vcpu, 0);
    if (m->run == MAP_FAILED) die("mmap kvm_run");

    if (ioctl(m->vcpu, KVM_GET_SREGS, &sregs) < 0)
        die("KVM_GET_SREGS");
    sregs.cr0 = 0x11;
    sregs.cr3 = 0;
    sregs.cr4 = 0;
    sregs.efer = 0;
    sregs.gdt.base = GDT_GPA;
    sregs.gdt.limit = sizeof bootstrap_gdt - 1;
    set_segment(&sregs.cs, 0x08, 1);
    set_segment(&sregs.ds, 0x10, 0);
    set_segment(&sregs.es, 0x10, 0);
    set_segment(&sregs.fs, 0x10, 0);
    set_segment(&sregs.gs, 0x10, 0);
    set_segment(&sregs.ss, 0x10, 0);
    if (ioctl(m->vcpu, KVM_SET_SREGS, &sregs) < 0)
        die("KVM_SET_SREGS");
    memset(&regs, 0, sizeof regs);
    regs.rip = 0;
    regs.rflags = 2;
    if (ioctl(m->vcpu, KVM_SET_REGS, &regs) < 0)
        die("KVM_SET_REGS");
}
