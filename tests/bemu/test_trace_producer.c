/*
 * Unit tests for the JSON Lines trace producer.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "../../bemu/trace.h"
#include "../../bemu/trace_clock.h"

static int failures = 0;

static int make_temp(char *out, size_t out_size)
{
    int fd;
    strncpy(out, "/tmp/test_trace_producer.XXXXXX", out_size);
    out[out_size - 1] = '\0';
    fd = mkstemp(out);
    return fd;
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

static int read_file(const char *path, char **out)
{
    FILE *f;
    long sz;
    f = fopen(path, "r");
    if (!f)
        return -1;
    if (fseek(f, 0, SEEK_END) < 0) {
        fclose(f);
        return -1;
    }
    sz = ftell(f);
    if (sz < 0) {
        fclose(f);
        return -1;
    }
    rewind(f);
    *out = malloc((size_t)sz + 1);
    if (!*out) {
        fclose(f);
        return -1;
    }
    if ((long)fread(*out, 1, (size_t)sz, f) != sz) {
        free(*out);
        fclose(f);
        return -1;
    }
    (*out)[sz] = '\0';
    fclose(f);
    return 0;
}

static int line_count(const char *s)
{
    int n = 0;
    const char *p;
    for (p = s; *p; p++)
        if (*p == '\n')
            n++;
    return n;
}

static const char *find_line(const char *s, const char *needle)
{
    const char *p = s;
    while (*p) {
        const char *nl = strchr(p, '\n');
        size_t len = nl ? (size_t)(nl - p) : strlen(p);
        if (strstr(p, needle))
            return p;
        p += len;
        if (*p == '\n')
            p++;
    }
    return NULL;
}

static void test_basic_events(void)
{
    struct trace_clock tc;
    struct trace t;
    char *content = NULL;
    char temp_path[64];
    int fd = make_temp(temp_path, sizeof(temp_path));
    check(fd >= 0, "mkstemp succeeded");
    if (fd < 0)
        return;
    close(fd);

    trace_clock_reset(&tc);
    check(trace_open(&t, &tc, temp_path) == 0, "trace_open succeeded");
    trace_event_boot(&t, "build/kernel.bin", "build/root.img", 8, 1);
    trace_clock_tick(&tc);
    trace_event_kvm_exit(&t, 2, "KVM_EXIT_IO");
    trace_event_io_access(&t, "out", 0x3f8, 1, 65);
    trace_event_irq(&t, 1, "raise");
    trace_event_timer(&t, 0x40, "latch");
    trace_event_input(&t, (const uint8_t *)"x", 1, "script");
    trace_event_shutdown(&t, "halt", 1000, 0);
    trace_close(&t);

    check(read_file(temp_path, &content) == 0, "read trace file");
    check(line_count(content) == 7, "seven events emitted");
    check(find_line(content, "\"type\":\"boot_start\"") != NULL, "boot_start event");
    check(find_line(content, "\"type\":\"kvm_exit\"") != NULL, "kvm_exit event");
    check(find_line(content, "\"type\":\"io_access\"") != NULL, "io_access event");
    check(find_line(content, "\"type\":\"irq\"") != NULL, "irq event");
    check(find_line(content, "\"type\":\"timer\"") != NULL, "timer event");
    check(find_line(content, "\"type\":\"input\"") != NULL, "input event");
    check(find_line(content, "\"bytes\":1") != NULL, "input bytes");
    check(find_line(content, "\"hex\":\"78\"") != NULL, "input hex");
    check(find_line(content, "\"type\":\"shutdown\"") != NULL, "shutdown event");
    check(find_line(content, "\"kernel\":\"build/kernel.bin\"") != NULL, "kernel field");
    check(find_line(content, "\"exit_count\":1") != NULL, "exit_count increments");
    check(find_line(content, "\"direction\":\"out\"") != NULL, "io direction");
    free(content);
    unlink(temp_path);
}

static void test_syscall_interrupt_process(void)
{
    struct trace_clock tc;
    struct trace t;
    char *content = NULL;
    char temp_path[64];
    uint64_t args[6] = {1, 2, 3, 4, 5, 6};
    int fd = make_temp(temp_path, sizeof(temp_path));
    check(fd >= 0, "mkstemp succeeded (2)");
    if (fd < 0)
        return;
    close(fd);

    trace_clock_reset(&tc);
    check(trace_open(&t, &tc, temp_path) == 0, "trace_open succeeded (2)");
    trace_event_syscall(&t, 1, args, 6);
    trace_event_interrupt(&t, 0x80);
    trace_event_process(&t, 1, "fork", "init");
    trace_close(&t);

    check(read_file(temp_path, &content) == 0, "read trace file (2)");
    check(line_count(content) == 3, "three events emitted");
    check(find_line(content, "\"type\":\"syscall\"") != NULL, "syscall event");
    check(find_line(content, "\"number\":1") != NULL, "syscall number");
    check(find_line(content, "\"args\":[1,2,3,4,5,6]") != NULL, "syscall args");
    check(find_line(content, "\"type\":\"interrupt\"") != NULL, "interrupt event");
    check(find_line(content, "\"vector\":128") != NULL, "interrupt vector");
    check(find_line(content, "\"type\":\"process\"") != NULL, "process event");
    check(find_line(content, "\"pid\":1") != NULL, "process pid");
    check(find_line(content, "\"action\":\"fork\"") != NULL, "process action");
    check(find_line(content, "\"name\":\"init\"") != NULL, "process name");
    free(content);
    unlink(temp_path);
}

static void test_disabled(void)
{
    struct trace t;
    trace_open(&t, NULL, NULL);
    trace_event_boot(&t, "k", "r", 8, 1);
    check(t.file == stderr, "disabled trace writes to stderr");
    trace_close(&t);
}

static int emit_schema_fixture(const char *path)
{
    struct trace_clock tc;
    struct trace t;
    uint64_t args[6] = {1, 2, 3, 4, 5, 6};

    trace_clock_reset(&tc);
    if (trace_open(&t, &tc, path) < 0)
        return 1;
    trace_event_boot(&t, "build/kernel.bin", "build/root.img", 8, 1);
    trace_clock_tick(&tc);
    trace_event_kvm_exit(&t, 2, "KVM_EXIT_IO");
    trace_event_io_access(&t, "out", 0x3f8, 1, 65);
    trace_event_irq(&t, 1, "raise");
    trace_event_timer(&t, 0x40, "latch");
    trace_event_input(&t, (const uint8_t *)"x", 1, "script");
    trace_event_syscall(&t, 1, args, 6);
    trace_event_interrupt(&t, 0x80);
    trace_event_process(&t, 1, "fork", "init");
    trace_event_shutdown(&t, "halt", 1, 0);
    trace_close(&t);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc == 3 && strcmp(argv[1], "--emit-schema-fixture") == 0)
        return emit_schema_fixture(argv[2]);
    test_basic_events();
    test_syscall_interrupt_process();
    test_disabled();
    if (failures) {
        fprintf(stderr, "\n%d test(s) failed\n", failures);
        return 1;
    }
    printf("\nall trace-producer tests passed\n");
    return 0;
}
