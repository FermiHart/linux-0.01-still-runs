#include "trace.h"

#include <string.h>
#include <stdlib.h>

static void emit_string(FILE *f, const char *s)
{
    const char *p;
    if (!s) {
        fprintf(f, "null");
        return;
    }
    fputc('"', f);
    for (p = s; *p; p++) {
        unsigned char c = (unsigned char)*p;
        switch (c) {
        case '"':  fputs("\\\"", f); break;
        case '\\': fputs("\\\\", f); break;
        case '\b': fputs("\\b", f); break;
        case '\f': fputs("\\f", f); break;
        case '\n': fputs("\\n", f); break;
        case '\r': fputs("\\r", f); break;
        case '\t': fputs("\\t", f); break;
        default:
            if (c < 0x20)
                fprintf(f, "\\u%04x", c);
            else
                fputc(c, f);
            break;
        }
    }
    fputc('"', f);
}

int trace_open(struct trace *t, struct trace_clock *tc, const char *path)
{
    t->clock = tc;
    t->exit_count = 0;
    if (!tc || !path) {
        t->file = stderr;
        t->enabled = (tc != NULL);
        return 0;
    }
    if (strcmp(path, "-") == 0) {
        t->file = stderr;
    } else {
        t->file = fopen(path, "w");
        if (!t->file)
            return -1;
        setvbuf(t->file, NULL, _IOFBF, 1 << 20);
    }
    t->enabled = 1;
    return 0;
}

void trace_close(struct trace *t)
{
    if (!t || !t->enabled)
        return;
    if (t->file && t->file != stderr) {
        fclose(t->file);
        t->file = NULL;
    }
    t->enabled = 0;
}

static void emit_header(struct trace *t, const char *type)
{
    fprintf(t->file, "{\"ts\":%llu,\"type\":", (unsigned long long)trace_clock_now(t->clock));
    emit_string(t->file, type);
    fprintf(t->file, ",\"data\":");
}

static void emit_footer(struct trace *t)
{
    fprintf(t->file, "}\n");
}

void trace_event_boot(struct trace *t, const char *kernel, const char *root, unsigned ram_mib,
                      unsigned trace_version)
{
    if (!t || !t->enabled)
        return;
    emit_header(t, "boot_start");
    fprintf(t->file, "{\"kernel\":");
    emit_string(t->file, kernel);
    fprintf(t->file, ",\"root\":");
    emit_string(t->file, root);
    fprintf(t->file, ",\"ram_mib\":%u,\"trace_version\":%u}", ram_mib, trace_version);
    emit_footer(t);
}

void trace_event_kvm_exit(struct trace *t, unsigned exit_reason, const char *reason_name)
{
    if (!t || !t->enabled)
        return;
    t->exit_count++;
    emit_header(t, "kvm_exit");
    fprintf(t->file, "{\"exit_reason\":%u,\"exit_reason_name\":", exit_reason);
    emit_string(t->file, reason_name);
    fprintf(t->file, ",\"exit_count\":%lu}", t->exit_count);
    emit_footer(t);
}

void trace_event_io_access(struct trace *t, const char *direction,
                           uint16_t port, unsigned size, uint32_t value)
{
    if (!t || !t->enabled)
        return;
    emit_header(t, "io_access");
    fprintf(t->file, "{\"direction\":");
    emit_string(t->file, direction);
    fprintf(t->file, ",\"port\":%u,\"size\":%u,\"value\":%u}", port, size, value);
    emit_footer(t);
}

void trace_event_irq(struct trace *t, unsigned irq, const char *action)
{
    if (!t || !t->enabled)
        return;
    emit_header(t, "irq");
    fprintf(t->file, "{\"irq\":%u,\"action\":", irq);
    emit_string(t->file, action);
    fprintf(t->file, "}");
    emit_footer(t);
}

void trace_event_timer(struct trace *t, uint16_t port, const char *action)
{
    if (!t || !t->enabled)
        return;
    emit_header(t, "timer");
    fprintf(t->file, "{\"port\":%u,\"action\":", port);
    emit_string(t->file, action);
    fprintf(t->file, "}");
    emit_footer(t);
}

void trace_event_input(struct trace *t, size_t bytes, const char *source)
{
    if (!t || !t->enabled)
        return;
    emit_header(t, "input");
    fprintf(t->file, "{\"bytes\":%zu,\"source\":", bytes);
    emit_string(t->file, source);
    fprintf(t->file, "}");
    emit_footer(t);
}

void trace_event_syscall(struct trace *t, unsigned number,
                         const uint64_t *args, unsigned nargs)
{
    unsigned i;
    if (!t || !t->enabled)
        return;
    if (nargs > 6)
        nargs = 6;
    emit_header(t, "syscall");
    fprintf(t->file, "{\"number\":%u,\"args\":[", number);
    for (i = 0; i < nargs; i++) {
        if (i)
            fprintf(t->file, ",");
        fprintf(t->file, "%llu", (unsigned long long)args[i]);
    }
    fprintf(t->file, "]}");
    emit_footer(t);
}

void trace_event_interrupt(struct trace *t, unsigned vector)
{
    if (!t || !t->enabled)
        return;
    emit_header(t, "interrupt");
    fprintf(t->file, "{\"vector\":%u}", vector);
    emit_footer(t);
}

void trace_event_process(struct trace *t, unsigned pid,
                         const char *action, const char *name)
{
    if (!t || !t->enabled)
        return;
    emit_header(t, "process");
    fprintf(t->file, "{\"pid\":%u,\"action\":", pid);
    emit_string(t->file, action);
    fprintf(t->file, ",\"name\":");
    emit_string(t->file, name);
    fprintf(t->file, "}");
    emit_footer(t);
}

void trace_event_shutdown(struct trace *t, const char *reason,
                          unsigned long exits, int status)
{
    if (!t || !t->enabled)
        return;
    emit_header(t, "shutdown");
    fprintf(t->file, "{\"reason\":");
    emit_string(t->file, reason);
    fprintf(t->file, ",\"exits\":%lu,\"status\":%d}", exits, status);
    emit_footer(t);
}
