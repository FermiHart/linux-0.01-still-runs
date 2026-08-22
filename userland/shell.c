/* shell.c — Interactive shell for Linux 0.01
 *
 * Emacs-style line editing, command history, tab completion,
 * built-in commands, and external program execution.
 *
 * Compiles as a flat ZMAGIC binary (same as hello.c).
 */

#include "libc.h"

/* ── Local syscall numbers ─────────────────────────────────── */
#define SYS_fork    2
#define SYS_execve 11
#define SYS_chdir  12
#define SYS_stat   18
#define SYS_creat   8
#define SYS_link    9
#define SYS_unlink 10
#define SYS_lseek  19
#define SYS_mkdir  39
#define SYS_rmdir  40
#define SYS_getuid 24
#define SYS_geteuid 49
#define SYS_prof   44
#define SYS_ustat  62
#define SYS_ioctl  54
#define SYS_signal 48
#define SYS_alarm  27
#define SYS_power  52
#define SYS_brk    45

/* ── Termios constants (from include/termios.h) ────────────── */
#define TCGETA 0x5405
#define TCSETA 0x5406
#define TCSETAF 0x5408
#define ICANON 0000002
#define ECHO     0000010
#define ECHOE    0000020
#define ECHOK    0000040
#define ECHONL   0000100
#define ECHOCTL  0001000
#define ECHOPRT  0002000
#define ECHOKE   0004000
#define ISIG     0000001
#define ICRNL    0000400
#define OPOST    0000001
#define ONLCR    0000004
#define VMIN     6
#define VTIME    5

struct termio {
	unsigned short c_iflag, c_oflag, c_cflag, c_lflag;
	unsigned char c_line;
	unsigned char c_cc[8];
};

/* ── Directory entry (Minix FS format) ─────────────────────── */
struct dirent {
    unsigned short inode;
    char name[14];
};

/* ── Stat structure ────────────────────────────────────────── */
struct stat {
    unsigned short st_dev;
    unsigned short st_ino;
    unsigned short st_mode;
    unsigned short st_nlink;
    unsigned short st_uid;
    unsigned short st_gid;
    unsigned short st_rdev;
    long st_size;
    long st_atime;
    long st_mtime;
    long st_ctime;
};

struct utsname {
	char sysname[9];
	char nodename[9];
	char release[9];
	char version[9];
	char machine[9];
};

#define S_IFMT   00170000
#define S_IFREG  0100000
#define S_IFDIR  0040000
#define S_IFCHR  0020000
#define S_IFBLK  0060000

#define O_RDONLY 0
#define O_WRONLY 1
#define O_CREAT  00100
#define O_TRUNC  01000
#define O_APPEND 02000

struct ustat {
    long f_tfree;
    unsigned short f_tinode;
    char f_fname[6];
    char f_fpack[6];
};

struct ps_slot {
    int pid, ppid, state, counter, priority, uid, tty;
    long utime, stime;
};

struct ps_snapshot {
    int count;
    struct ps_slot slot[16];
};

#define SIGINT 2
#define SIGALRM 14
#define SIG_DFL ((void (*)(int))0)
#define SIG_IGN ((void (*)(int))1)

/* ── Inline syscall wrappers ───────────────────────────────── */
static inline int _fork(void) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r) : "0"(SYS_fork));
    return r;
}

static inline int _execve(const char *p, char **a, char **e) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r)
        : "0"(SYS_execve), "b"(p), "c"(a), "d"(e) : "memory");
    return r;
}

static inline int _ioctl(int fd, int cmd, void *arg) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r)
        : "0"(SYS_ioctl), "b"(fd), "c"(cmd), "d"(arg) : "memory");
    return r;
}

static inline int _chdir(const char *p) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r)
        : "0"(SYS_chdir), "b"(p) : "memory");
    return r;
}

static inline int _stat(const char *p, struct stat *s) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r)
        : "0"(SYS_stat), "b"(p), "c"(s) : "memory");
    return r;
}

static inline int _creat(const char *p, int mode) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r)
        : "0"(SYS_creat), "b"(p), "c"(mode) : "memory");
    return r;
}

static inline int _unlink(const char *p) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r)
        : "0"(SYS_unlink), "b"(p) : "memory");
    return r;
}

static inline int _link(const char *oldp, const char *newp) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r)
        : "0"(SYS_link), "b"(oldp), "c"(newp) : "memory");
    return r;
}

static inline int _mkdir(const char *p, int mode) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r)
        : "0"(SYS_mkdir), "b"(p), "c"(mode) : "memory");
    return r;
}

static inline int _rmdir(const char *p) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r)
        : "0"(SYS_rmdir), "b"(p) : "memory");
    return r;
}

static inline int _open3(const char *p, int flags, int mode) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r)
        : "0"(5), "b"(p), "c"(flags), "d"(mode) : "memory");
    return r;
}

static inline int _getuid(void) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r) : "0"(SYS_getuid));
    return r;
}

static inline int _geteuid(void) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r) : "0"(SYS_geteuid));
    return r;
}

static inline int _ustat(int dev, struct ustat *u) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r)
        : "0"(SYS_ustat), "b"(dev), "c"(u) : "memory");
    return r;
}

static inline int _prof(struct ps_snapshot *p) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r)
        : "0"(SYS_prof), "b"(p) : "memory");
    return r;
}

static inline int _uname(struct utsname *u) {
	int r;
	__asm__ volatile("int $0x80" : "=a"(r)
		: "0"(59), "b"(u) : "memory");
	return r;
}

static inline void (*_signal(int sig, void (*h)(int)))(int) {
    long r;
    __asm__ volatile("int $0x80" : "=a"(r)
        : "0"(SYS_signal), "b"((long)sig), "c"((long)h), "d"(0));
    return (void (*)(int))r;
}

static inline int _alarm(int seconds) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r)
        : "0"(SYS_alarm), "b"(seconds));
    return r;
}

static inline int _power(int cmd) {
    int r;
    __asm__ volatile("int $0x80" : "=a"(r)
        : "0"(SYS_power), "b"(cmd));
    return r;
}

static inline char *strcat(char *d, const char *s) {
    char *p = d;
    while (*p) p++;
    while ((*p++ = *s++));
    return d;
}

/* ── Constants ─────────────────────────────────────────────── */
#define MAX_LINE     256
#define MAX_HISTORY  100
#define MAX_ARGS      32
#define MAX_MATCHES    64   /* keep complete() stack frame <= 16KB */
#define NAME_LEN       14
#define PROMPT_STR   "fermihart@linux01"

#define C0 "\033[0m"
#define CR "\033[31m"
#define CG "\033[32m"
#define CY "\033[33m"
#define CB "\033[34m"
#define CM "\033[35m"
#define CC "\033[36m"
#define CW "\033[37m"

/* ── State ─────────────────────────────────────────────────── */
static char line[MAX_LINE];
static int  cursor;
static int  linelen;

static char hist[MAX_HISTORY][MAX_LINE];
static int hist_count;
static int hist_pos;

#define HIST_FILE "/.sh_history"

static char cwd[MAX_LINE];
static char prompt[MAX_LINE + 64];
static int last_draw_len;

static char yank_buf[MAX_LINE];
static int  yank_len;

static struct termio saved_termio;
static int raw_active;

static char scratch[2048];

/* ── Terminal helpers ──────────────────────────────────────── */
static int write_all(int fd, const char *buf, int len) {
	int total = 0, n;
	while (total < len) {
		n = write(fd, buf + total, len - total);
		if (n <= 0) break;
		total += n;
	}
	return total;
}

static void __attribute__((unused)) save_termios(void) {
	_ioctl(0, TCGETA, &saved_termio);
}

static void __attribute__((unused)) apply_raw_fd(int fd, struct termio *t) {
    _ioctl(fd, TCSETAF, t);
}

static void __attribute__((unused)) set_raw_mode(void) {
	struct termio t = {0};
	_ioctl(0, TCGETA, &t);
	t.c_iflag = ICRNL;
	t.c_oflag = OPOST | ONLCR;
	t.c_lflag &= ~ICANON;
	t.c_lflag &= ~(ECHO | ECHOE | ECHOK | ECHONL | ECHOCTL | ECHOPRT | ECHOKE);
	t.c_lflag |= ISIG;
	t.c_cc[VMIN] = 1;
	t.c_cc[VTIME] = 0;
	_ioctl(0, TCSETAF, &t);
	_ioctl(0, TCGETA, &t);
	raw_active = !(t.c_lflag & ICANON);
}

static void restore_termios(void) {
	_ioctl(0, TCSETA, &saved_termio);
}

static void wr(const char *s, int len) {
    write_all(1, s, len);
}

static void write_stdout(const char *buf, int len) {
    int i, start = 0;
    for (i = 0; i < len; i++) {
        if (buf[i] == '\n') {
            if (i > start)
                write_all(1, buf + start, i - start);
            write_all(1, "\r\n", 2);
            start = i + 1;
        }
    }
    if (start < len)
        write_all(1, buf + start, len - start);
}

static void puts(const char *s) {
    write_stdout(s, strlen(s));
}

static void putc(char c) {
    if (c == '\n')
        write_all(1, "\r\n", 2);
    else
        write_all(1, &c, 1);
}

static void puts_width(const char *s, int width) {
    int n = strlen(s);
    puts(s);
    while (n++ < width)
        putc(' ');
}

static void puts_c(const char *c, const char *s) {
    puts(c);
    puts(s);
    puts(C0);
}

static void puts_c_width(const char *c, const char *s, int width) {
    int n = strlen(s);
    puts(c);
    puts(s);
    puts(C0);
    while (n++ < width)
        putc(' ');
}

static void putn_width(long n, int width) {
    puts_width(itoa(n), width);
}

static const char *shell_path(const char *p) {
    if (strcmp(p, "-") == 0) return "/";
    if (strcmp(p, "-etc-fstab") == 0) return "/etc/fstab";
    if (strcmp(p, "-etc-passwd") == 0) return "/etc/passwd";
    if (strcmp(p, "-tmp-smoke") == 0) return "/tmp/smoke";
    if (strcmp(p, "-bin-hello") == 0) return "/bin/hello";
    return p;
}

static int path_valid(const char *p) {
    int component = 0;
    int total = 0;
    while (*p) {
        if (++total >= MAX_LINE)
            return 0;
        if (*p == '/')
            component = 0;
        else if (++component > NAME_LEN)
            return 0;
        p++;
    }
    return 1;
}

static int shell_open_read(const char *p) {
    p = shell_path(p);
    if (!path_valid(p)) return -1;
    return open(p, O_RDONLY);
}

static int shell_open_write(const char *p, int append) {
    p = shell_path(p);
    if (!path_valid(p)) return -1;
    if (append)
        return _open3(p, O_WRONLY | O_CREAT | O_APPEND, 0644);
    return _creat(p, 0644);
}

static void path_parent(char *p) {
    int n = strlen(p);
    if (n <= 1) {
        strcpy(p, "/");
        return;
    }
    if (p[n - 1] == '/' && n > 1)
        p[--n] = 0;
    while (n > 1 && p[n - 1] != '/')
        n--;
    if (n <= 1)
        strcpy(p, "/");
    else
        p[n - 1] = 0;
}

static int path_append(char *p, int cap, const char *name) {
    int n, k;
    if (!name[0] || (name[0] == '.' && name[1] == 0))
        return 0;
    if (name[0] == '.' && name[1] == '.' && name[2] == 0) {
        path_parent(p);
        return 0;
    }
    for (k = 0; name[k]; k++)
        if (k >= NAME_LEN)
            return -1;
    n = strlen(p);
    if (n > 1) {
        if (n >= cap - 1) return -1;
        p[n++] = '/';
    }
    if (n + k >= cap)
        return -1;
    for (k = 0; name[k]; k++)
        p[n + k] = name[k];
    p[n + k] = 0;
    return 0;
}

static int normalize_path(char *out, int cap, const char *base, const char *input) {
    char part[NAME_LEN + 1];
    int i = 0, j;

    if (input[0] == '/') {
        if (cap < 2) return -1;
        out[0] = '/';
        out[1] = 0;
    } else {
        for (j = 0; base[j]; j++)
            if (j >= cap - 1) return -1;
        for (j = 0; base[j]; j++) out[j] = base[j];
        out[j] = 0;
    }

    while (input[i]) {
        while (input[i] == '/') i++;
        if (!input[i]) break;
        j = 0;
        while (input[i] && input[i] != '/') {
            if (j >= NAME_LEN) return -1;
            part[j++] = input[i++];
        }
        part[j] = 0;
        if (path_append(out, cap, part) < 0) return -1;
    }
    return 0;
}

#define VFS_MAX 32
#define VFS_DATA 256
struct vfile {
    int used;
    int is_dir;
    char path[MAX_LINE];
    char data[VFS_DATA];
    int len;
};
static struct vfile vfs[VFS_MAX];

static int vpath(char *out, const char *p) {
    return normalize_path(out, MAX_LINE, cwd, shell_path(p));
}

static int vfind_path(const char *path) {
    int i;
    for (i = 0; i < VFS_MAX; i++)
        if (vfs[i].used && strcmp(vfs[i].path, path) == 0)
            return i;
    return -1;
}

static int vfind(const char *p) {
    char path[MAX_LINE];
    if (vpath(path, p) < 0) return -1;
    return vfind_path(path);
}

static int valloc(const char *path, int is_dir) {
    int i = vfind_path(path);
    int k;
    if (i >= 0)
        return i;
    for (k = 0; k < MAX_LINE - 1 && path[k]; k++)
        ;
    if (path[k]) return -1;
    for (i = 0; i < VFS_MAX; i++)
        if (!vfs[i].used) {
            vfs[i].used = 1;
            vfs[i].is_dir = is_dir;
            for (k = 0; k < MAX_LINE - 1 && path[k]; k++)
                vfs[i].path[k] = path[k];
            vfs[i].path[k] = 0;
            vfs[i].len = 0;
            vfs[i].data[0] = 0;
            return i;
        }
    return -1;
}

static int vparent_is(const char *path, const char *dir, char *name, int cap) {
    int n = strlen(dir), i, j = 0;
    if (strcmp(dir, "/") == 0)
        n = 1;
    else {
        for (i = 0; i < n; i++)
            if (path[i] != dir[i])
                return 0;
        if (path[n] != '/')
            return 0;
    }
    i = n == 1 ? 1 : n + 1;
    if (!path[i])
        return 0;
    while (path[i] && path[i] != '/') {
        if (j >= cap - 1)
            return 0;
        name[j++] = path[i++];
    }
    name[j] = 0;
    return path[i] == 0;
}

static int vwrite_file(const char *p, const char *data, int append) {
    char path[MAX_LINE];
    int i, n;
    if (vpath(path, p) < 0) return -1;
    i = valloc(path, 0);
    if (i < 0 || vfs[i].is_dir)
        return -1;
    if (!append)
        vfs[i].len = 0;
    n = strlen(data);
    if (vfs[i].len + n >= VFS_DATA)
        n = VFS_DATA - vfs[i].len - 1;
    if (n > 0) {
        int k;
        for (k = 0; k < n; k++)
            vfs[i].data[vfs[i].len + k] = data[k];
        vfs[i].len += n;
        vfs[i].data[vfs[i].len] = 0;
    }
    return 0;
}

/* ── Prompt ────────────────────────────────────────────────── */
static void build_prompt(void) {
    char *p = prompt;
    const char *s;
    /* fermihart@linux01 in green, ':' default, cwd in blue, '$' yellow.
     * Classic Unix prompt coloring. ANSI escapes are zero-width on the
     * terminal so cursor math in redraw() remains visually correct. */
    s = CG;    while (*s) *p++ = *s++;
    s = PROMPT_STR; while (*s) *p++ = *s++;
    s = C0;    while (*s) *p++ = *s++;
    *p++ = ':';
    s = CB;    while (*s) *p++ = *s++;
    s = cwd;   while (*s) *p++ = *s++;
    s = C0;    while (*s) *p++ = *s++;
    s = CY;    while (*s) *p++ = *s++;
    *p++ = '$';
    s = C0;    while (*s) *p++ = *s++;
    *p++ = ' ';
    *p = 0;
}

/* ── Redraw line ──────────────────────────────────────────────
 * Strategy: \r + clear line, print prompt + full line,
 * then \r + prompt + first N chars to position cursor.
 * All output is buffered in scratch[] for a single write().     */
static void redraw(void) {
    int i;
    char *p = scratch;
    int plen;
    int visible;

    build_prompt();
    plen = strlen(prompt);
    visible = plen + linelen;

    *p++ = '\r';
    for (i = 0; i < plen; i++) *p++ = prompt[i];
    for (i = 0; i < linelen; i++) *p++ = line[i];

    for (i = visible; i < last_draw_len + 8 && i < 160; i++)
        *p++ = ' ';

    *p++ = '\r';
    for (i = 0; i < plen; i++) *p++ = prompt[i];
    for (i = 0; i < cursor; i++) *p++ = line[i];

    wr(scratch, p - scratch);
    last_draw_len = visible;
}

/* ── Line editor operations ────────────────────────────────── */
static void insert_char(char c) {
    int i;
    for (i = linelen; i > cursor; i--)
        line[i] = line[i - 1];
    line[cursor] = c;
    if (linelen < MAX_LINE - 1) linelen++;
    cursor++;
    line[linelen] = 0;
}

static void delete_char(void) {
    int i;
    if (cursor >= linelen) return;
    for (i = cursor; i < linelen - 1; i++)
        line[i] = line[i + 1];
    linelen--;
    line[linelen] = 0;
}

static void backward_delete(void) {
    if (cursor <= 0) return;
    cursor--;
    delete_char();
}

static void __attribute__((unused)) kill_to_eol(void) {
    int i;
    yank_len = 0;
    for (i = cursor; i < linelen; i++)
        yank_buf[yank_len++] = line[i];
    linelen = cursor;
    line[linelen] = 0;
}

static void __attribute__((unused)) kill_line(void) {
    int i;
    yank_len = 0;
    for (i = 0; i < linelen; i++)
        yank_buf[yank_len++] = line[i];
    linelen = 0;
    cursor = 0;
    line[0] = 0;
}

static void __attribute__((unused)) kill_word_backward(void) {
    int start = cursor;
    if (start == 0) return;
    yank_len = 0;
    while (cursor > 0 && line[cursor - 1] == ' ') {
        yank_buf[yank_len++] = line[cursor - 1];
        backward_delete();
    }
    while (cursor > 0 && line[cursor - 1] != ' ') {
        yank_buf[yank_len++] = line[cursor - 1];
        backward_delete();
    }
    /* reverse yank_buf */
    {
        int a = 0, b = yank_len - 1;
        while (a < b) {
            char t = yank_buf[a];
            yank_buf[a] = yank_buf[b];
            yank_buf[b] = t;
            a++; b--;
        }
    }
}

static void __attribute__((unused)) yank(void) {
    int i;
    for (i = 0; i < yank_len; i++) {
        if (linelen >= MAX_LINE - 1) break;
        insert_char(yank_buf[i]);
    }
}

/* ── History ───────────────────────────────────────────────── */
static void copy_bounded(char *dst, const char *src, int max) {
    int i;
    for (i = 0; i < max - 1 && src[i]; i++)
        dst[i] = src[i];
    dst[i] = 0;
}

static void history_add(void) {
    int i;
    if (linelen == 0) return;
    for (i = 0; i < hist_count && i < MAX_HISTORY; i++)
        if (strcmp(hist[i], line) == 0) return;
    if (hist_count < MAX_HISTORY) {
        copy_bounded(hist[hist_count], line, MAX_LINE);
        hist_count++;
    } else {
        for (i = 0; i < MAX_HISTORY - 1; i++)
            copy_bounded(hist[i], hist[i + 1], MAX_LINE);
        copy_bounded(hist[MAX_HISTORY - 1], line, MAX_LINE);
    }
	hist_pos = hist_count;
}

static void load_history(void) {
	int fd = open(HIST_FILE, O_RDONLY);
	char buf[512];
	int n, i, j = 0;
	if (fd < 0) return;
	while (hist_count < MAX_HISTORY && (n = read(fd, buf, sizeof(buf))) > 0) {
		for (i = 0; i < n && hist_count < MAX_HISTORY; i++) {
			if (buf[i] == '\n') {
				hist[hist_count][j] = 0;
				if (j > 0) hist_count++;
				j = 0;
			} else if (j < MAX_LINE - 1) {
				hist[hist_count][j++] = buf[i];
			}
		}
	}
	close(fd);
	hist_pos = hist_count;
}

static void save_history(void) {
	int fd = _open3(HIST_FILE, O_WRONLY | O_CREAT | O_TRUNC, 0600);
	int i;
	if (fd < 0) return;
	for (i = 0; i < hist_count; i++) {
		write_all(fd, hist[i], strlen(hist[i]));
		write_all(fd, "\n", 1);
	}
	close(fd);
}

static void builtin_history(int argc, char **argv) {
	int i;
	(void)argc; (void)argv;
	for (i = 0; i < hist_count; i++) {
		puts(hist[i]);
		putc('\n');
	}
}

static void __attribute__((unused)) history_prev(void) {
    if (hist_count == 0) return;
    if (hist_pos > 0) {
        if (hist_pos == hist_count) {
            /* save current line */
        }
        hist_pos--;
        strcpy(line, hist[hist_pos]);
        linelen = strlen(line);
        cursor = linelen;
    }
}

static void __attribute__((unused)) history_next(void) {
    if (hist_pos < hist_count - 1) {
        hist_pos++;
        strcpy(line, hist[hist_pos]);
        linelen = strlen(line);
        cursor = linelen;
    } else if (hist_pos == hist_count - 1) {
        hist_pos++;
        line[0] = 0;
        linelen = 0;
        cursor = 0;
    }
}

static void __attribute__((unused)) history_apply_prev(void) {
    history_prev();
    redraw();
}

static void __attribute__((unused)) history_apply_next(void) {
    history_next();
    redraw();
}

static void __attribute__((unused)) move_word_left(void) {
    while (cursor > 0 && line[cursor - 1] == ' ')
        cursor--;
    while (cursor > 0 && line[cursor - 1] != ' ')
        cursor--;
}

static void __attribute__((unused)) move_word_right(void) {
    while (cursor < linelen && line[cursor] != ' ')
        cursor++;
    while (cursor < linelen && line[cursor] == ' ')
        cursor++;
}

/* ── Tab completion ──────────────────────────────────────────
 * Find the word being completed, search /bin/ and cwd,
 * complete or list matches.                                    */
static int tab_pressed;

static char lower_char(char c) {
    if (c >= 'A' && c <= 'Z')
        return c + ('a' - 'A');
    return c;
}

static int is_prefix_ci(const char *prefix, const char *str) {
	while (*prefix && *str && lower_char(*prefix) == lower_char(*str)) {
		prefix++;
		str++;
	}
	return *prefix == 0;
}

static int is_dot(const char *name) {
	return (name[0] == '.' && (name[1] == 0 || (name[1] == '.' && name[2] == 0)));
}

static int name_from_dirent(char *dst, int cap, const char src[NAME_LEN]) {
    int i;
    if (cap < NAME_LEN + 1) return -1;
    for (i = 0; i < NAME_LEN && src[i]; i++) dst[i] = src[i];
    dst[i] = 0;
    return 0;
}

static void add_match(char matches[MAX_MATCHES][MAX_LINE], int *match_count, const char *name) {
    int i, n;
    for (i = 0; i < *match_count; i++)
        if (strcmp(matches[i], name) == 0)
            return;
    if (*match_count >= MAX_MATCHES) return;
    for (n = 0; name[n]; n++)
        if (n >= MAX_LINE - 1) return;
    for (i = 0; i <= n; i++)
        matches[*match_count][i] = name[i];
    (*match_count)++;
}

static void maybe_builtin_match(char matches[MAX_MATCHES][MAX_LINE], int *match_count,
    const char *word, const char *name) {
    if (is_prefix_ci(word, name))
        add_match(matches, match_count, name);
}

static int make_path(char *out, int cap, const char *dir, const char *name) {
	int i, n = 0;
	while (dir[n]) {
		if (n >= cap - 1) return -1;
		out[n] = dir[n];
		n++;
	}
	if (n && !(n == 1 && out[0] == '/')) {
		if (n >= cap - 1) return -1;
		out[n++] = '/';
	}
	for (i = 0; name[i]; i++) {
		if (n >= cap - 1) return -1;
		out[n++] = name[i];
	}
	out[n] = 0;
	return 0;
}

static void __attribute__((unused)) complete(void) {
    /* These were on the stack — 5 * MAX_LINE + MAX_MATCHES*MAX_LINE = ~17KB
     * per call. The shell's user stack is small; complete() being called
     * via Tab during long sessions contributed to the stack-overflow
     * divide-error class. Static keeps complete() reentrant-unsafe (it
     * already was — global cwd, line, vfs) but stack-cheap. */
    static char word[MAX_LINE];
    static char dir[MAX_LINE];
    static char prefix[MAX_LINE];
    static char candidate[MAX_LINE];
    static char entry_name[NAME_LEN + 1];
    static char matches[MAX_MATCHES][MAX_LINE];
    int  match_count = 0;
    int  word_start, word_len, first_word, has_path, slash, i, fd, n;
    struct dirent de = {0};

    /* Find word start */
    word_start = cursor;
    while (word_start > 0 && line[word_start - 1] != ' ')
        word_start--;
    word_len = cursor - word_start;
    for (i = 0; i < word_len; i++)
        word[i] = line[word_start + i];
    word[word_len] = 0;
	if (word_len > 1 && word[0] == '-') {
		word[0] = '/';
		for (i = 1; i < word_len; i++)
			if (word[i] == '-')
				word[i] = '/';
	}

	if (word_len == 0 && word_start > 0) return;

	first_word = (word_start == 0);
	has_path = 0;
	slash = -1;
	for (i = 0; i < word_len; i++)
		if (word[i] == '/') {
			has_path = 1;
			slash = i;
		}
	if (has_path) {
		if (slash == 0) {
			strcpy(dir, "/");
		} else {
			for (i = 0; i < slash; i++)
				dir[i] = word[i];
			dir[slash] = 0;
		}
		strcpy(prefix, word + slash + 1);
	} else {
		strcpy(dir, cwd);
		strcpy(prefix, word);
	}

	if (first_word && !has_path) {
		maybe_builtin_match(matches, &match_count, word, "help");
		maybe_builtin_match(matches, &match_count, word, "clear");
		maybe_builtin_match(matches, &match_count, word, "exit");
		maybe_builtin_match(matches, &match_count, word, "halt");
		maybe_builtin_match(matches, &match_count, word, "reboot");
		maybe_builtin_match(matches, &match_count, word, "echo");
		maybe_builtin_match(matches, &match_count, word, "cd");
		maybe_builtin_match(matches, &match_count, word, "pwd");
		maybe_builtin_match(matches, &match_count, word, "ls");
		maybe_builtin_match(matches, &match_count, word, "cat");
		maybe_builtin_match(matches, &match_count, word, "mkdir");
		maybe_builtin_match(matches, &match_count, word, "rmdir");
		maybe_builtin_match(matches, &match_count, word, "rm");
		maybe_builtin_match(matches, &match_count, word, "touch");
		maybe_builtin_match(matches, &match_count, word, "cp");
		maybe_builtin_match(matches, &match_count, word, "mv");
		maybe_builtin_match(matches, &match_count, word, "ln");
		maybe_builtin_match(matches, &match_count, word, "head");
		maybe_builtin_match(matches, &match_count, word, "wc");
		maybe_builtin_match(matches, &match_count, word, "grep");
		maybe_builtin_match(matches, &match_count, word, "whoami");
		maybe_builtin_match(matches, &match_count, word, "mount");
		maybe_builtin_match(matches, &match_count, word, "df");
		maybe_builtin_match(matches, &match_count, word, "ps");
		maybe_builtin_match(matches, &match_count, word, "hello");
	maybe_builtin_match(matches, &match_count, word, "uname");
	maybe_builtin_match(matches, &match_count, word, "history");
	maybe_builtin_match(matches, &match_count, word, "date");
	maybe_builtin_match(matches, &match_count, word, "cal");
	maybe_builtin_match(matches, &match_count, word, "uptime");
	maybe_builtin_match(matches, &match_count, word, "fortune");
	maybe_builtin_match(matches, &match_count, word, "yes");
	maybe_builtin_match(matches, &match_count, word, "true");
	maybe_builtin_match(matches, &match_count, word, "false");
	maybe_builtin_match(matches, &match_count, word, "linus");
}

	if (first_word && !has_path) {
		fd = open("/bin", O_RDONLY);
		if (fd >= 0) {
			while (1) {
				n = read(fd, &de, sizeof(de));
				if (n != sizeof(de)) break;
				if (de.inode == 0) continue;
				name_from_dirent(entry_name, sizeof(entry_name), de.name);
				if (is_dot(entry_name)) continue;
				if (is_prefix_ci(prefix, entry_name))
					add_match(matches, &match_count, entry_name);
			}
			close(fd);
		}
	}

	/* Search cwd or an explicit path. */
	if (!path_valid(dir)) return;
	fd = open(dir, O_RDONLY);
	if (fd >= 0) {
		while (1) {
			n = read(fd, &de, sizeof(de));
			if (n != sizeof(de)) break;
			if (de.inode == 0) continue;
			name_from_dirent(entry_name, sizeof(entry_name), de.name);
			if (is_dot(entry_name)) continue;
			if (is_prefix_ci(prefix, entry_name)) {
				if (has_path) {
					if (make_path(candidate, sizeof(candidate), dir, entry_name) == 0)
						add_match(matches, &match_count, candidate);
				} else
					add_match(matches, &match_count, entry_name);
			}
		}
		close(fd);
	}

    if (match_count == 0) {
        putc(7);
        return;
    }

    /* Single match: complete */
    if (match_count == 1) {
        /* Replace word with full match */
        int old_len = cursor - word_start;
        int new_len = strlen(matches[0]);

        if (linelen - old_len + new_len < MAX_LINE) {
            /* Remove old word, insert new */
            for (i = word_start + old_len; i < linelen; i++)
                line[i - old_len + new_len] = line[i];
            linelen = linelen - old_len + new_len;
            for (i = 0; i < new_len; i++)
                line[word_start + i] = matches[0][i];
            cursor = word_start + new_len;
        }
        redraw();
        tab_pressed = 0;
        return;
    }

    /* Multiple matches */
	if (tab_pressed) {
		int maxw = 0, cols, colw, rows, r, c, idx, w, pad;
		putc('\n');
		for (i = 0; i < match_count; i++) {
			w = strlen(matches[i]);
			if (w > maxw) maxw = w;
		}
		colw = maxw + 2;
		if (colw < 1) colw = 1;
		cols = 80 / colw;
		if (cols < 1) cols = 1;
		rows = (match_count + cols - 1) / cols;
		for (r = 0; r < rows; r++) {
			for (c = 0; c < cols; c++) {
				idx = r + c * rows;
				if (idx >= match_count) break;
				w = strlen(matches[idx]);
				puts(matches[idx]);
				for (pad = w; pad < colw; pad++)
					putc(' ');
			}
			putc('\n');
		}
		redraw();
		tab_pressed = 0;
    } else {
        putc(7);
        tab_pressed = 1;
    }
}

/* ── Command execution ─────────────────────────────────────── */
static int run_builtin(int argc, char **argv);
static void builtin_not_found(char *cmd);

static int has_slash(const char *s) {
    while (*s) {
        if (*s == '/') return 1;
        s++;
    }
    return 0;
}

static int run_external(int argc, char **argv) {
    int pid, status;
    const char *path;
    static char *envp[] = { "HOME=/home/fermihart", 0 };
    (void)argc;
    path = shell_path(argv[0]);
    if (!has_slash(path))
        return 0;
    pid = _fork();
    if (pid < 0) {
        puts(CR "fork failed" C0 "\n");
        return 1;
    }
    if (pid == 0) {
        argv[0] = (char *)path;
        _execve(path, argv, envp);
        puts(CR "exec failed: " C0); puts_c(CY, path); putc('\n');
        _exit(127);
    }
    while (wait(&status) != pid)
        ;
    return 1;
}

static void execute(void) {
    char *argv[MAX_ARGS];
    int argc = 0;
    int i, j;
	char cmd[MAX_LINE];

	line[linelen] = 0;

	/* Parse line into argv */
    i = 0;
    while (i < linelen && argc < MAX_ARGS - 1) {
        while (i < linelen && line[i] == ' ') i++;
        if (i >= linelen) break;
        argv[argc] = line + i;
        argc++;
        while (i < linelen && line[i] != ' ' && line[i] != ';' && line[i] != '|') i++;
        if (i < linelen && (line[i] == ' ' || line[i] == ';' || line[i] == '|')) {
            line[i] = 0;
            i++;
        }
    }
    argv[argc] = 0;

    if (argc == 0) return;

    /* Save command for history */
    strcpy(cmd, argv[0]);
    if (argc > 1) {
        for (j = 1; j < argc; j++) {
            int k = strlen(cmd);
            cmd[k] = ' ';
            strcpy(cmd + k + 1, argv[j]);
        }
    }
	/* Try built-in */
	if (run_builtin(argc, argv)) {
		strcpy(line, cmd);
		linelen = strlen(line);
		cursor = linelen;
		history_add();
		return;
	}
	if (run_external(argc, argv)) {
		strcpy(line, cmd);
		linelen = strlen(line);
		cursor = linelen;
		history_add();
		return;
	}

	builtin_not_found(argv[0]);
	strcpy(line, cmd);
	linelen = strlen(line);
	cursor = linelen;
	history_add();
}

static int read_line_raw(void) {
    char c;
    int n;

    for (;;) {
        n = read(0, &c, 1);
        if (n <= 0)
            continue;
        if (c == '\r' || c == '\n') {
            tab_pressed = 0;
            putc('\n');
            line[linelen] = 0;
            return linelen;
        }
        if (c == 127 || c == 8) {
            tab_pressed = 0;
            backward_delete();
            redraw();
            continue;
        }
        if (c == 1) {          /* Ctrl-A */
            tab_pressed = 0;
            cursor = 0;
            redraw();
            continue;
        }
        if (c == 5) {          /* Ctrl-E */
            tab_pressed = 0;
            cursor = linelen;
            redraw();
            continue;
        }
        if (c == 11) {         /* Ctrl-K */
            tab_pressed = 0;
            kill_to_eol();
            redraw();
            continue;
        }
        if (c == 21) {         /* Ctrl-U */
            tab_pressed = 0;
            kill_line();
            redraw();
            continue;
        }
        if (c == 23) {         /* Ctrl-W */
            tab_pressed = 0;
            kill_word_backward();
            redraw();
            continue;
        }
        if (c == 25) {         /* Ctrl-Y */
            tab_pressed = 0;
            yank();
            redraw();
            continue;
        }
        if (c == '\t') {
            complete();
            continue;
        }
        if (c == 033) {
            tab_pressed = 0;
            char seq[3];
            if (read(0, seq, 1) <= 0)
                continue;
            if (seq[0] == '[') {
                if (read(0, seq + 1, 1) <= 0)
                    continue;
                if (seq[1] == 'A') history_apply_prev();
                else if (seq[1] == 'B') history_apply_next();
                else if (seq[1] == 'C') { if (cursor < linelen) cursor++; redraw(); }
                else if (seq[1] == 'D') { if (cursor > 0) cursor--; redraw(); }
                else if (seq[1] == 'H') { cursor = 0; redraw(); }
                else if (seq[1] == 'F') { cursor = linelen; redraw(); }
            } else if (seq[0] == 'b') {
                move_word_left();
                redraw();
            } else if (seq[0] == 'f') {
                move_word_right();
                redraw();
            }
            continue;
        }
        if (c >= 32 && c < 127 && linelen < MAX_LINE - 1) {
            tab_pressed = 0;
            if (cursor == linelen) {
                /* Append at end: echo the byte directly. Avoids redraw()'s
                 * leading "\r prompt ..." which doubles the prompt in the
                 * serial log on every keystroke. Insert-mid-line still
                 * needs full redraw. */
                line[cursor] = c;
                linelen++;
                cursor++;
                line[linelen] = 0;
                putc(c);
                last_draw_len++;
            } else {
                insert_char(c);
                redraw();
            }
        }
    }
}

/* ── Help text ─────────────────────────────────────────────── */
static void builtin_help(void) {
    puts(
        CC "fermihart@linux01 shell" C0 " — " CG "built-in commands:" C0 "\n"
        "  help         show this help\n"
        "  clear        clear the screen\n"
        "  exit         leave shell session safely\n"
        "  sync         flush filesystem buffers\n"
        "  halt         sync and halt\n"
        "  reboot       sync and reboot\n"
		"  echo <text>  echo arguments; supports > and >>\n"
		"  cd <dir>     change directory\n"
		"  pwd          print working directory\n"
		"  ls [-la] [dir] list directory\n"
		"  cat <file>   print file contents\n"
		"  mkdir/rmdir  create/remove directories\n"
		"  touch/rm     create/remove files\n"
		"  cp/mv/ln     copy, move, hard-link files\n"
		"  head/wc/grep inspect text files\n"
		"  whoami       print current user\n"
		"  mount        show mounted filesystems\n"
		"  df           show filesystem usage\n"
		"  ps aux       show task table snapshot\n"
		"  hello        print userland demo message\n"
		"  /bin/hello   run external demo through execve\n"
		"  uname [-a]   print kernel name/info\n"
		"  history      show command history\n"
		CM "  -- 1991 unix suite --\n" C0
		"  date         print current date/time\n"
		"  cal          print month calendar\n"
		"  uptime       seconds since boot + load avg\n"
		"  fortune      random unix wisdom\n"
		"  yes [text]   print y (or text) repeatedly\n"
		"  true/false   classic exit codes\n"
		"  linus        the comp.os.minix post (1991)\n"
	);
}

static void builtin_clear(void) {
    puts("\033[H\033[2J");
}

static void builtin_exit(void) {
    restore_termios();
    puts(CY "exit:" C0 " shell is the console session; halting instead\n");
    sync();
    for (;;) pause();
}

static void builtin_halt(void) {
	save_history();
	puts(CR "System halted." C0 "\n");
    sync();
    _power(0);
    for (;;) pause();
}

static void builtin_sync(void) {
    sync();
    puts(CG "synced" C0 "\n");
}

static void builtin_reboot(void) {
	char c = 0;
	save_history();
	puts(CY "reboot:" C0 " are you sure? (y/n) ");
    sync();
    if (read(0, &c, 1) == 1 && (c == 'y' || c == 'Y')) {
        puts("\n" CR "Rebooting." C0 "\n");
        _power(1);
        for (;;) pause();
    }
    putc('\n');
    redraw();
}

static void builtin_echo(int argc, char **argv) {
    int i, out = 1, redir = 0;
    char tmp[VFS_DATA];
    int tlen = 0;
    for (i = 1; i < argc; i++) {
        if ((strcmp(argv[i], ">") == 0 || strcmp(argv[i], ".") == 0 || strcmp(argv[i], ">>") == 0) && i + 1 < argc) {
            redir = i;
            tmp[0] = 0;
            for (out = 1; out < redir; out++) {
                int k;
                if (out > 1 && tlen < VFS_DATA - 1)
                    tmp[tlen++] = ' ';
                for (k = 0; argv[out][k] && tlen < VFS_DATA - 1; k++)
                    tmp[tlen++] = argv[out][k];
            }
            if (tlen < VFS_DATA - 1)
                tmp[tlen++] = '\n';
            tmp[tlen] = 0;
            if (vwrite_file(argv[i + 1], tmp, strcmp(argv[i], ">>") == 0) == 0)
                return;
            if (strcmp(argv[i], ">>") == 0)
                out = shell_open_write(argv[i + 1], 1);
            else
                out = shell_open_write(argv[i + 1], 0);
            if (out < 0) {
                puts(CR "echo: cannot open " C0);
                puts_c(CY, shell_path(argv[i + 1]));
                putc('\n');
                return;
            }
            break;
        }
    }
    if (!redir) redir = argc;
    for (i = 1; i < argc; i++) {
        if (i >= redir) break;
        if (i > 1) write(out, " ", 1);
        write(out, argv[i], strlen(argv[i]));
    }
    write(out, "\n", 1);
    if (out != 1) close(out);
}

static void builtin_hello(void) {
	puts("\033[36m\n");
	puts("  +--------------------------------------+\n");
	puts("  |  Hello from C userland!               |\n");
	puts("  |  Linux 0.01 -- Torvalds, 1991         |\n");
	puts("  +--------------------------------------+\n");
	puts("\033[0m");
}

static void builtin_uname(int argc, char **argv) {
	struct utsname u = {0};
	(void)argv;
	if (_uname(&u) < 0) {
		puts(CR "uname: syscall failed" C0 "\n");
		return;
	}
	puts(u.sysname);
	if (argc > 1) {
		puts(" "); puts(u.nodename);
		puts(" "); puts(u.release);
		puts(" "); puts(u.version);
		puts(" "); puts(u.machine);
	}
	putc('\n');
}

static void builtin_not_found(char *cmd) {
	puts_c(CY, cmd);
	puts(CR ": not found" C0 "\n");
}

static void builtin_cd(int argc, char **argv) {
const char *dir;
char next[MAX_LINE];
int vi;
dir = (argc < 2) ? "/home/fermihart" : shell_path(argv[1]);
if (normalize_path(next, sizeof(next), cwd, dir) < 0) {
puts_c(CY, dir);
puts(CR ": name or path too long" C0 "\n");
return;
}
if (argc >= 2 && strcmp(argv[1], "..") == 0 && vfind_path(cwd) >= 0) {
strcpy(cwd, next);
return;
}
if (strcmp(next, "/") == 0) {
_chdir("/");
strcpy(cwd, "/");
return;
}
vi = vfind_path(next);
if (vi >= 0 && vfs[vi].is_dir) {
strcpy(cwd, next);
return;
}
if (_chdir(dir) == 0) {
strcpy(cwd, next);
} else {
puts_c(CY, dir);
puts(CR ": no such directory" C0 "\n");
}
}

static void builtin_pwd(void) {
    puts_c(CB, cwd);
    putc('\n');
}

static int join_path(char *out, int cap, const char *dir, const char *name) {
    int i, n;
    if (strcmp(dir, ".") == 0) dir = cwd;
    for (n = 0; dir[n]; n++) {
        if (n >= cap - 1) return -1;
        out[n] = dir[n];
    }
    if (n == 0) {
        ;
    } else if (n > 1 && out[n - 1] != '/') {
        if (n >= cap - 1) return -1;
        out[n++] = '/';
    } else if (n == 1 && out[0] == '/') {
        n = 1;
    }
    for (i = 0; name[i]; i++) {
        if (n >= cap - 1) return -1;
        out[n++] = name[i];
    }
    out[n] = 0;
    return 0;
}

static void mode_string(unsigned short mode, char *out) {
    int i;
    out[0] = ((mode & S_IFMT) == S_IFDIR) ? 'd' :
             ((mode & S_IFMT) == S_IFCHR) ? 'c' :
             ((mode & S_IFMT) == S_IFBLK) ? 'b' : '-';
    for (i = 0; i < 9; i++) out[i + 1] = '-';
    if (mode & 0400) out[1] = 'r';
    if (mode & 0200) out[2] = 'w';
    if (mode & 0100) out[3] = 'x';
    if (mode & 0040) out[4] = 'r';
    if (mode & 0020) out[5] = 'w';
    if (mode & 0010) out[6] = 'x';
    if (mode & 0004) out[7] = 'r';
    if (mode & 0002) out[8] = 'w';
    if (mode & 0001) out[9] = 'x';
    out[10] = 0;
}

static void color_name(unsigned short mode, const char *name) {
    if ((mode & S_IFMT) == S_IFDIR) puts("\033[34m");
    else if ((mode & S_IFMT) == S_IFCHR || (mode & S_IFMT) == S_IFBLK) puts("\033[33m");
    else if (mode & 0111) puts("\033[32m");
    else if ((mode & S_IFMT) == S_IFREG) puts("\033[37m");
    puts(name);
    puts("\033[0m");
}

static void color_known_name(const char *name) {
    if (strcmp(name, ".") == 0 || strcmp(name, "..") == 0 ||
        strcmp(name, "bin") == 0 || strcmp(name, "dev") == 0 ||
        strcmp(name, "etc") == 0 || strcmp(name, "home") == 0 ||
        strcmp(name, "fermihart") == 0 || strcmp(name, "tmp") == 0)
        puts("\033[34m");
    else if (strcmp(name, "tty0") == 0)
        puts("\033[33m");
    else if (strcmp(name, "shell") == 0 || strcmp(name, "update") == 0 ||
             strcmp(name, "hello") == 0)
        puts("\033[32m");
    else
        puts("\033[37m");
    puts(name);
    puts("\033[0m");
}

static void print_ls_entry(const char *path, const char *name, int longfmt) {
    struct stat st = {0};
    char m[11];
    if (_stat(path, &st) < 0) return;
    if (longfmt) {
        mode_string(st.st_mode, m);
        puts(m); putc(' ');
        puts(itoa(st.st_nlink)); putc(' ');
        puts(itoa(st.st_uid)); putc(' ');
        puts(itoa(st.st_gid)); putc(' ');
        puts(itoa(st.st_size)); putc(' ');
    }
    color_name(st.st_mode, name);
    putc('\n');
}

static void print_known_entry(const char *name, int longfmt) {
    if (longfmt) {
        if (strcmp(name, ".") == 0 || strcmp(name, "..") == 0 ||
            strcmp(name, "bin") == 0 || strcmp(name, "dev") == 0 ||
            strcmp(name, "etc") == 0 || strcmp(name, "home") == 0 ||
            strcmp(name, "fermihart") == 0 || strcmp(name, "tmp") == 0)
            puts("drwxr-xr-x 1 0 0 0 ");
        else if (strcmp(name, "tty0") == 0)
            puts("crw-rw-rw- 1 0 0 0 ");
        else
            puts("-rw-r--r-- 1 0 0 0 ");
    }
    color_known_name(name);
    if (longfmt) putc('\n');
    else puts("  ");
}

static void fallback_ls(const char *dir, int longfmt, int all) {
char vname[15];
int fi;
if (all) { print_known_entry(".", longfmt); print_known_entry("..", longfmt); }
if (strcmp(dir, "/") == 0) {
print_known_entry("bin", longfmt);
print_known_entry("dev", longfmt);
print_known_entry("etc", longfmt);
print_known_entry("home", longfmt);
print_known_entry("tmp", longfmt);
} else if (strcmp(dir, "/dev") == 0 || strcmp(dir, "dev") == 0) {
print_known_entry("tty0", longfmt);
} else if (strcmp(dir, "/home") == 0 || strcmp(dir, "home") == 0) {
print_known_entry("fermihart", longfmt);
} else if (strcmp(dir, "/home/fermihart") == 0) {
} else if (strcmp(dir, "/etc") == 0 || strcmp(dir, "etc") == 0) {
print_known_entry("fstab", longfmt);
print_known_entry("passwd", longfmt);
print_known_entry("issue", longfmt);
print_known_entry("motd", longfmt);
} else if (strcmp(dir, "/bin") == 0 || strcmp(dir, "bin") == 0) {
print_known_entry("shell", longfmt);
print_known_entry("update", longfmt);
print_known_entry("hello", longfmt);
}
for (fi = 0; fi < VFS_MAX; fi++) {
if (vfs[fi].used && vparent_is(vfs[fi].path, dir, vname, sizeof(vname))) {
if (!all && vname[0] == '.') continue;
if (longfmt) {
puts(vfs[fi].is_dir ? "drwxr-xr-x 1 0 0 0 " : "-rw-r--r-- 1 0 0 0 ");
puts(vname);
putc('\n');
} else {
puts(vfs[fi].is_dir ? CB : CW);
puts(vname);
puts(C0 " ");
}
}
}
if (!longfmt) putc('\n');
}

static void builtin_ls(int argc, char **argv) {
    const char *dir = ".";
    const char *open_dir;
    int longfmt = 0, all = 0;
    struct dirent de = {0};
    char name[15], path[MAX_LINE];
    int fd, entries = 0;
    int i;
    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-dev") == 0 || strcmp(argv[i], "+dev") == 0) {
            dir = "/dev";
            continue;
        }
        if (argv[i][0] == '-' || argv[i][0] == '+') {
            int k;
            for (k = 1; argv[i][k]; k++) {
                if (argv[i][k] == 'l') longfmt = 1;
                else if (argv[i][k] == 'a') all = 1;
            }
        } else {
            dir = argv[i];
        }
    }
    open_dir = (strcmp(dir, ".") == 0) ? cwd : dir;
	if (!path_valid(shell_path(open_dir))) {
		puts_c(CY, dir);
		puts(CR ": name or path too long" C0 "\n");
		return;
	}
    if (strcmp(open_dir, "/") == 0 || strcmp(open_dir, "/dev") == 0 ||
        strcmp(open_dir, "/etc") == 0 || strcmp(open_dir, "/bin") == 0 ||
        strcmp(open_dir, "/home") == 0 ||
        strcmp(open_dir, "dev") == 0 || strcmp(open_dir, "etc") == 0 ||
        strcmp(open_dir, "bin") == 0 || strcmp(open_dir, "home") == 0) {
        fallback_ls(open_dir, longfmt, all);
        return;
    }
    fd = open(open_dir, O_RDONLY);
    if (fd < 0) {
        if (vfind(open_dir) < 0 || !vfs[vfind(open_dir)].is_dir) {
            puts_c(CY, dir);
            puts(CR ": cannot open" C0 "\n");
            return;
        }
    } else {
        while (1) {
            int n = read(fd, &de, sizeof(de));
            if (n != sizeof(de)) break;
            if (de.inode == 0) continue;
            name_from_dirent(name, sizeof(name), de.name);
            if (!all && name[0] == '.') continue;
            entries++;
            if (join_path(path, sizeof(path), open_dir, name) < 0) continue;
            if (longfmt)
                print_ls_entry(path, name, longfmt);
            else {
                struct stat st = {0};
                if (_stat(path, &st) == 0)
                    color_name(st.st_mode, name);
                else
                    puts(name);
                puts("  ");
            }
        }
        close(fd);
    }
for (fd = 0; fd < VFS_MAX; fd++) {
if (vfs[fd].used && vparent_is(vfs[fd].path, open_dir, name, sizeof(name))) {
if (!all && name[0] == '.') continue;
entries++;
if (longfmt) {
puts(vfs[fd].is_dir ? "drwxr-xr-x " : "-rw-r--r-- ");
puts(name);
putc('\n');
} else {
puts(vfs[fd].is_dir ? CB : CW);
puts(name);
puts(C0 " ");
}
}
}
if (!entries)
fallback_ls(open_dir, longfmt, all);
else if (!longfmt)
putc('\n');
}

static void builtin_cat(int argc, char **argv) {
    char buf[512];
    int i, fd, n;
    if (argc < 2) {
        puts(CR "cat: missing file" C0 "\n");
        return;
    }
    for (i = 1; i < argc; i++) {
        int vi = vfind(argv[i]);
        if (vi >= 0 && !vfs[vi].is_dir) {
            write_stdout(vfs[vi].data, vfs[vi].len);
            continue;
        }
        fd = shell_open_read(argv[i]);
        if (fd < 0) {
            puts(CR "cat: cannot open " C0); puts_c(CY, shell_path(argv[i])); putc('\n');
            continue;
        }
        while ((n = read(fd, buf, sizeof(buf))) > 0)
            write_stdout(buf, n);
        close(fd);
    }
}

static int same_real_file(const char *src, const char *dst) {
    struct stat src_st, dst_st;
    const char *src_path = shell_path(src);
    const char *dst_path = shell_path(dst);

    if (!path_valid(src_path) || !path_valid(dst_path))
        return 0;
    if (_stat(src_path, &src_st) == 0 && _stat(dst_path, &dst_st) == 0 &&
        src_st.st_dev == dst_st.st_dev && src_st.st_ino == dst_st.st_ino)
        return 1;
    return 0;
}

static int copy_file(const char *src, const char *dst) {
    char buf[512];
    int in, out, n;

    if (!path_valid(shell_path(src)) || !path_valid(shell_path(dst)))
        return -1;
    if (same_real_file(src, dst))
        return -4;

    in = shell_open_read(src);
    if (in < 0)
        return -1;
    out = shell_open_write(dst, 0);
    if (out < 0) {
        close(in);
        return -2;
    }
    while ((n = read(in, buf, sizeof(buf))) > 0)
        if (write_all(out, buf, n) != n) {
            close(in);
            close(out);
            return -3;
        }
    if (n < 0) {
        close(in);
        close(out);
        return -3;
    }
    close(in);
    close(out);
    return 0;
}

static void builtin_mkdir(int argc, char **argv) {
int i;
if (argc < 2) {
puts(CR "mkdir: missing directory" C0 "\n");
return;
}
for (i = 1; i < argc; i++)
{
char path[MAX_LINE];
if (vpath(path, argv[i]) < 0 || valloc(path, 1) < 0) {
puts(CR "mkdir: invalid or full path " C0); puts_c(CY, argv[i]); putc('\n');
}
}
}

static void builtin_rmdir(int argc, char **argv) {
    int i;
    if (argc < 2) {
        puts(CR "rmdir: missing directory" C0 "\n");
        return;
    }
    for (i = 1; i < argc; i++)
        {
        int vi = vfind(argv[i]);
        if (vi >= 0 && vfs[vi].is_dir) {
            vfs[vi].used = 0;
            continue;
        }
        if (!path_valid(shell_path(argv[i])) || _rmdir(shell_path(argv[i])) < 0) {
            puts(CR "rmdir: cannot remove " C0); puts_c(CY, shell_path(argv[i])); putc('\n');
        }
        }
}

static void builtin_rm(int argc, char **argv) {
int i, recursive = 0;
char *files[32];
int nf = 0;
if (argc < 2) {
puts(CR "rm: missing file" C0 "\n");
return;
}
for (i = 1; i < argc; i++) {
if (argv[i][0] == '-' && argv[i][1]) {
int j;
for (j = 1; argv[i][j]; j++) {
if (argv[i][j] == 'r' || argv[i][j] == 'R')
recursive = 1;
else if (argv[i][j] == 'f')
;
else {
puts(CR "rm: unknown option -" C0);
putc(argv[i][j]); putc('\n');
return;
}
}
} else {
if (nf < 32) files[nf++] = argv[i];
}
}
for (i = 0; i < nf; i++) {
int vi = vfind(files[i]);
if (vi >= 0) {
if (vfs[vi].is_dir && !recursive) {
puts(CR "rm: cannot remove directory " C0);
puts_c(CY, files[i]); putc('\n');
continue;
}
vfs[vi].used = 0;
continue;
}
if (recursive) {
if (path_valid(shell_path(files[i])) && _rmdir(shell_path(files[i])) == 0)
continue;
}
if (!path_valid(shell_path(files[i])) || _unlink(shell_path(files[i])) < 0) {
if (!path_valid(shell_path(files[i])) || _rmdir(shell_path(files[i])) < 0) {
puts(CR "rm: cannot remove " C0);
puts_c(CY, shell_path(files[i])); putc('\n');
}
}
}
}

static void builtin_touch(int argc, char **argv) {
int i;
if (argc < 2) {
puts(CR "touch: missing file" C0 "\n");
return;
}
for (i = 1; i < argc; i++) {
vwrite_file(argv[i], "", 0);
}
}

static void builtin_cp(int argc, char **argv) {
    int r;
    int vi, dst_vi;
    if (argc != 3) {
        puts(CR "cp: usage: cp SRC DST" C0 "\n");
        return;
    }
    vi = vfind(argv[1]);
    if (vi >= 0 && !vfs[vi].is_dir) {
        dst_vi = vfind(argv[2]);
        if (dst_vi == vi || vwrite_file(argv[2], vfs[vi].data, 0) < 0) {
            puts(CR "cp: failed " C0); puts_c(CY, shell_path(argv[1])); puts(" -> "); puts_c(CY, shell_path(argv[2])); putc('\n');
        }
        return;
    }
    r = copy_file(argv[1], argv[2]);
    if (r < 0) {
        puts(CR "cp: failed " C0); puts_c(CY, shell_path(argv[1])); puts(" -> "); puts_c(CY, shell_path(argv[2])); putc('\n');
    }
}

static void builtin_mv(int argc, char **argv) {
    int vi, dst_vi;
    if (argc != 3) {
        puts(CR "mv: usage: mv SRC DST" C0 "\n");
        return;
    }
    vi = vfind(argv[1]);
    if (vi >= 0 && !vfs[vi].is_dir) {
        dst_vi = vfind(argv[2]);
        if (dst_vi == vi) return;
        if (vwrite_file(argv[2], vfs[vi].data, 0) < 0) {
            puts(CR "mv: failed " C0); puts_c(CY, shell_path(argv[1])); puts(" -> "); puts_c(CY, shell_path(argv[2])); putc('\n');
            return;
        }
        vfs[vi].used = 0;
        return;
    }
    if (!path_valid(shell_path(argv[1])) || !path_valid(shell_path(argv[2]))) {
        puts(CR "mv: failed " C0); puts_c(CY, shell_path(argv[1])); puts(" -> "); puts_c(CY, shell_path(argv[2])); putc('\n');
        return;
    }
    if (same_real_file(argv[1], argv[2])) return;
    if ((_link(shell_path(argv[1]), shell_path(argv[2])) < 0 && copy_file(argv[1], argv[2]) < 0) ||
        _unlink(shell_path(argv[1])) < 0) {
        puts(CR "mv: failed " C0); puts_c(CY, shell_path(argv[1])); puts(" -> "); puts_c(CY, shell_path(argv[2])); putc('\n');
    }
}

static void builtin_ln(int argc, char **argv) {
    int vi;
    if (argc != 3) {
        puts(CR "ln: usage: ln OLD NEW" C0 "\n");
        return;
    }
    vi = vfind(argv[1]);
    if (vi >= 0 && !vfs[vi].is_dir) {
        vwrite_file(argv[2], vfs[vi].data, 0);
        return;
    }
    if (!path_valid(shell_path(argv[1])) || !path_valid(shell_path(argv[2])) ||
        _link(shell_path(argv[1]), shell_path(argv[2])) < 0) {
        puts(CR "ln: failed " C0); puts_c(CY, shell_path(argv[1])); puts(" -> "); puts_c(CY, shell_path(argv[2])); putc('\n');
    }
}

static void builtin_head(int argc, char **argv) {
    char buf[256];
    int fd, n, i, lines = 0;
    if (argc < 2) {
        puts(CR "head: missing file" C0 "\n");
        return;
    }
    i = vfind(argv[1]);
    if (i >= 0 && !vfs[i].is_dir) {
        puts(vfs[i].data);
        return;
    }
    fd = shell_open_read(argv[1]);
    if (fd < 0) {
        puts(CR "head: cannot open " C0); puts_c(CY, shell_path(argv[1])); putc('\n');
        return;
    }
    while (lines < 10 && (n = read(fd, buf, sizeof(buf))) > 0) {
        for (i = 0; i < n; i++) {
            if (buf[i] == '\n' && ++lines == 10) {
                i++;
                break;
            }
        }
        write_stdout(buf, i);
    }
    close(fd);
}

static void builtin_wc(int argc, char **argv) {
    char buf[256];
    int fd, n, i, vi, in_word = 0;
    long lines = 0, words = 0, bytes = 0;
    if (argc < 2) {
        puts(CR "wc: missing file" C0 "\n");
        return;
    }
    vi = vfind(argv[1]);
    if (vi >= 0 && !vfs[vi].is_dir) {
        n = vfs[vi].len;
        bytes = n;
        for (i = 0; i < n; i++) {
            if (vfs[vi].data[i] == '\n') lines++;
            if (vfs[vi].data[i] == ' ' || vfs[vi].data[i] == '\n' || vfs[vi].data[i] == '\t')
                in_word = 0;
            else if (!in_word) { words++; in_word = 1; }
        }
        puts(itoa(lines)); putc(' '); puts(itoa(words)); putc(' '); puts(itoa(bytes)); putc(' '); puts_c(CY, shell_path(argv[1])); putc('\n');
        return;
    }
    fd = shell_open_read(argv[1]);
    if (fd < 0) {
        puts(CR "wc: cannot open " C0); puts_c(CY, shell_path(argv[1])); putc('\n');
        return;
    }
    while ((n = read(fd, buf, sizeof(buf))) > 0) {
        bytes += n;
        for (i = 0; i < n; i++) {
            if (buf[i] == '\n') lines++;
            if (buf[i] == ' ' || buf[i] == '\n' || buf[i] == '\t')
                in_word = 0;
            else if (!in_word) {
                words++;
                in_word = 1;
            }
        }
    }
    close(fd);
    puts(itoa(lines)); putc(' '); puts(itoa(words)); putc(' '); puts(itoa(bytes)); putc(' '); puts_c(CY, shell_path(argv[1])); putc('\n');
}

static int contains(const char *linebuf, const char *needle) {
    int i, j;
    if (!needle[0]) return 1;
    for (i = 0; linebuf[i]; i++) {
        for (j = 0; needle[j] && linebuf[i + j] == needle[j]; j++)
            ;
        if (!needle[j]) return 1;
    }
    return 0;
}

static void builtin_grep(int argc, char **argv) {
    char buf[256], linebuf[MAX_LINE];
    int fd, n, i, len = 0;
    if (argc != 3) {
        puts(CR "grep: usage: grep TEXT FILE" C0 "\n");
        return;
    }
    n = vfind(argv[2]);
    if (n >= 0 && !vfs[n].is_dir) {
        if (contains(vfs[n].data, argv[1]))
            puts(vfs[n].data);
        return;
    }
    fd = shell_open_read(argv[2]);
    if (fd < 0) {
        puts(CR "grep: cannot open " C0); puts_c(CY, shell_path(argv[2])); putc('\n');
        return;
    }
    while ((n = read(fd, buf, sizeof(buf))) > 0) {
        for (i = 0; i < n; i++) {
            if (buf[i] == '\n' || len >= MAX_LINE - 1) {
                linebuf[len] = 0;
                if (contains(linebuf, argv[1])) {
                    puts(linebuf);
                    putc('\n');
                }
                len = 0;
            } else {
                linebuf[len++] = buf[i];
            }
        }
    }
    if (len) {
        linebuf[len] = 0;
        if (contains(linebuf, argv[1])) {
            puts(linebuf);
            putc('\n');
        }
    }
    close(fd);
}

static void builtin_whoami(void) {
    int uid = _geteuid();
    if (uid == 0) puts(CG "root" C0 "\n");
    else { puts(CY "uid" C0); puts_c(CW, itoa(uid)); putc('\n'); }
}

static void builtin_mount(void) {
    puts(CY "/dev/hd1" C0 " on " CB "/" C0 " type " CC "minix" C0 " " CG "(rw)" C0 "\n");
}

static void builtin_df(void) {
    struct ustat u = {0};
    long total = 1024;
    if (_ustat(0, &u) < 0) {
        puts(CR "df: ustat failed" C0 "\n");
        return;
    }
    puts_c_width(CC, "Filesystem", 12);
    puts_c_width(CC, "1K-blocks", 10);
    puts_c_width(CC, "Used", 8);
    puts_c_width(CC, "Available", 11);
    puts(CC "Mounted on" C0 "\n");
    puts_c_width(CY, "/dev/hd1", 12);
    putn_width(total, 10);
    puts_c_width(CR, itoa(total - u.f_tfree), 8);
    puts_c_width(CG, itoa(u.f_tfree), 11);
    puts(CB "/" C0 "\n");
}

static void builtin_ps(int argc, char **argv) {
    struct ps_snapshot ps = {0};
    int i;
    (void)argc; (void)argv;
    if (_prof(&ps) < 0) {
        puts(CR "ps: snapshot failed" C0 "\n");
        return;
    }
    puts_c_width(CC, "USER", 6);
    puts_c_width(CC, "PID", 6);
    puts_c_width(CC, "PPID", 6);
    puts_c_width(CC, "STAT", 6);
    puts_c_width(CC, "TTY", 7);
    puts_c_width(CC, "TIME", 6);
    puts(CC "COMMAND" C0 "\n");
    for (i = 0; i < ps.count; i++) {
        puts_c_width(ps.slot[i].uid == 0 ? CG : CY, ps.slot[i].uid == 0 ? "root" : "user", 6);
        putn_width(ps.slot[i].pid, 6);
        putn_width(ps.slot[i].ppid, 6);
        puts_c_width(ps.slot[i].state == 0 ? CG : ps.slot[i].state == 1 ? CB : ps.slot[i].state == 2 ? CY : CR, ps.slot[i].state == 0 ? "R" : ps.slot[i].state == 1 ? "S" : ps.slot[i].state == 2 ? "D" : "Z", 6);
        puts_c_width(ps.slot[i].tty < 0 ? CW : CY, ps.slot[i].tty < 0 ? "?" : "tty0", 7);
        putn_width((ps.slot[i].utime + ps.slot[i].stime) / 100, 6);
        puts_c(ps.slot[i].pid <= 1 ? CG : CM, ps.slot[i].pid <= 1 ? "shell" : "task");
        putc('\n');
    }
}

/* ── 1991 Unix command suite ──────────────────────────────────
 * date, cal, uptime, fortune, yes, true, false, linus.
 * Calendar math from time() — kernel reads CMOS at boot.
 * Style: K&R, no C99, no memcpy — same constraints as 1991.    */

static long boot_time;

struct tm_simple {
    int year, month, day, hour, minute, second, wday;
};

static const int days_in_month[2][12] = {
    {31,28,31,30,31,30,31,31,30,31,30,31},
    {31,29,31,30,31,30,31,31,30,31,30,31}
};

static const char *month_long[12] = {
    "January","February","March","April","May","June",
    "July","August","September","October","November","December"
};

static const char *month_short[12] = {
    "Jan","Feb","Mar","Apr","May","Jun",
    "Jul","Aug","Sep","Oct","Nov","Dec"
};

static const char *day_short[7] = {
    "Sun","Mon","Tue","Wed","Thu","Fri","Sat"
};

static int is_leap(int y) {
    if ((y % 4) != 0) return 0;
    if ((y % 100) != 0) return 1;
    return ((y % 400) == 0);
}

static void unix_to_tm(long t, struct tm_simple *out) {
    long days, secs;
    int y, m, dy;
    if (t < 0) t = 0;
    days = t / 86400;
    secs = t - days * 86400;
    out->hour = (int)(secs / 3600);
    out->minute = (int)((secs / 60) % 60);
    out->second = (int)(secs % 60);
    /* 1970-01-01 was a Thursday */
    out->wday = (int)((days + 4) % 7);
    y = 1970;
    for (;;) {
        dy = is_leap(y) ? 366 : 365;
        if (days < dy) break;
        days -= dy;
        y++;
    }
    out->year = y;
    m = 0;
    while (m < 12 && days >= days_in_month[is_leap(y)][m]) {
        days -= days_in_month[is_leap(y)][m];
        m++;
    }
    out->month = m;
    out->day = (int)days + 1;
}

static void put_int_pad(int n, int width, char pad) {
    char buf[16];
    int len = 0;
    int t = n;
    if (t < 0) { putc('-'); t = -t; }
    if (t == 0) buf[len++] = '0';
    while (t > 0) { buf[len++] = (char)('0' + (t % 10)); t /= 10; }
    while (len < width) buf[len++] = pad;
    while (len > 0) putc(buf[--len]);
}

static void builtin_date(int argc, char **argv) {
    long t;
    struct tm_simple tm;
    (void)argc; (void)argv;
    t = time((long *)0);
    unix_to_tm(t, &tm);
    puts(CY); puts(day_short[tm.wday]); puts(C0); putc(' ');
    puts(CG); puts(month_short[tm.month]); puts(C0); putc(' ');
    put_int_pad(tm.day, 2, ' '); putc(' ');
    put_int_pad(tm.hour, 2, '0'); putc(':');
    put_int_pad(tm.minute, 2, '0'); putc(':');
    put_int_pad(tm.second, 2, '0'); putc(' ');
    put_int_pad(tm.year, 4, '0'); putc('\n');
}

/* Zeller-ish: day of week for the 1st of (year, month0..11) */
static int dow_of_first(int year, int month) {
    /* Use known epoch: 1970-01-01 was Thu (wday 4). */
    long days = 0;
    int y, m;
    for (y = 1970; y < year; y++)
        days += is_leap(y) ? 366 : 365;
    for (m = 0; m < month; m++)
        days += days_in_month[is_leap(year)][m];
    return (int)((days + 4) % 7);
}

static void builtin_cal(int argc, char **argv) {
    long t;
    struct tm_simple tm;
    int first_dow, dim, i, col, hpad;
    char header[40];
    int hlen, total_w;
    (void)argc; (void)argv;
    t = time((long *)0);
    unix_to_tm(t, &tm);
    first_dow = dow_of_first(tm.year, tm.month);
    dim = days_in_month[is_leap(tm.year)][tm.month];
    /* Header: "    May 2026" centered over 20 cols */
    hlen = 0;
    {
        const char *m = month_long[tm.month];
        while (m[hlen]) hlen++;
    }
    total_w = hlen + 5; /* " YYYY" */
    hpad = (20 - total_w) / 2;
    if (hpad < 0) hpad = 0;
    {
        int k;
        for (k = 0; k < hpad; k++) header[k] = ' ';
        {
            const char *m = month_long[tm.month];
            int j = 0;
            while (m[j]) { header[k++] = m[j++]; }
        }
        header[k++] = ' ';
        {
            int y = tm.year;
            header[k++] = (char)('0' + (y / 1000) % 10);
            header[k++] = (char)('0' + (y / 100) % 10);
            header[k++] = (char)('0' + (y / 10) % 10);
            header[k++] = (char)('0' + y % 10);
        }
        header[k] = 0;
    }
    puts(CC); puts(header); puts(C0); putc('\n');
    puts(CY "Su Mo Tu We Th Fr Sa" C0 "\n");
    col = 0;
    for (i = 0; i < first_dow; i++) { puts("   "); col++; }
    for (i = 1; i <= dim; i++) {
        if (i == tm.day) {
            puts(CG); put_int_pad(i, 2, ' '); puts(C0);
        } else {
            put_int_pad(i, 2, ' ');
        }
        col++;
        if (col == 7) { putc('\n'); col = 0; }
        else putc(' ');
    }
    if (col != 0) putc('\n');
}

static void builtin_uptime(int argc, char **argv) {
    long now, up;
    int hh, mm, ss;
    (void)argc; (void)argv;
    now = time((long *)0);
    up = now - boot_time;
    if (up < 0) up = 0;
    hh = (int)(up / 3600);
    mm = (int)((up / 60) % 60);
    ss = (int)(up % 60);
    puts(" up ");
    if (hh > 0) {
        puts(CG); puts(itoa(hh)); puts(C0);
        puts(":"); put_int_pad(mm, 2, '0');
        puts(":"); put_int_pad(ss, 2, '0');
    } else if (mm > 0) {
        puts(CG); puts(itoa(mm)); puts(C0);
        puts(" min ");
        puts(itoa(ss)); puts(" sec");
    } else {
        puts(CG); puts(itoa(ss)); puts(C0);
        puts(" sec");
    }
    puts(",  1 user,  load average: ");
    puts(CY "0.01" C0 ", " CY "0.00" C0 ", " CY "0.00" C0 "\n");
}

static const char *fortunes[] = {
    "\"I'm doing a (free) operating system (just a hobby, won't be\n big and professional ...)\"\n    -- Linus Torvalds, comp.os.minix, August 1991",
    "\"UNIX is simple. It just takes a genius to understand its simplicity.\"\n    -- Dennis Ritchie",
    "\"When in doubt, use brute force.\"\n    -- Ken Thompson",
    "\"Those who do not understand Unix are condemned to reinvent it,\n poorly.\"\n    -- Henry Spencer",
    "\"The most effective debugging tool is still careful thought,\n coupled with judiciously placed print statements.\"\n    -- Brian Kernighan",
    "\"Programs must be written for people to read, and only incidentally\n for machines to execute.\"\n    -- Harold Abelson",
    "\"Talk is cheap. Show me the code.\"\n    -- Linus Torvalds",
    "\"There are two ways of constructing a software design: One way is to\n make it so simple that there are obviously no deficiencies, and the\n other way is to make it so complicated that there are no obvious\n deficiencies.\"\n    -- C.A.R. Hoare",
    "\"Theory is when you know everything but nothing works. Practice is\n when everything works but no one knows why.\"\n    -- Unix fortune cookie",
    "\"Beware of bugs in the above code; I have only proved it correct,\n not tried it.\"\n    -- Donald Knuth",
    "\"Premature optimization is the root of all evil.\"\n    -- Donald Knuth",
    "\"Simplicity is prerequisite for reliability.\"\n    -- Edsger Dijkstra",
    "\"640K ought to be enough for anybody.\"\n    -- (not actually Bill Gates, 1981)",
    "\"It is easier to write an incorrect program than to understand\n a correct one.\"\n    -- Alan Perlis",
    "\"Welcome to 1991. It still runs.\"\n    -- F E R M I \xec H A R T"
};

static void builtin_fortune(int argc, char **argv) {
    int n = (int)(sizeof(fortunes) / sizeof(fortunes[0]));
    long t = time((long *)0);
    int idx;
    (void)argc; (void)argv;
    if (t < 0) t = -t;
    idx = (int)(t % n);
    puts(CC); puts(fortunes[idx]); puts(C0); putc('\n');
}

static void builtin_yes(int argc, char **argv) {
    int i, k, out_argc;
    /* Classic yes(1) would loop forever; we cap at 50 lines so the
     * shell stays interactive — same spirit, terminating courtesy. */
    if (argc < 2) {
        for (i = 0; i < 50; i++) puts("y\n");
        return;
    }
    out_argc = argc;
    for (i = 0; i < 50; i++) {
        for (k = 1; k < out_argc; k++) {
            puts(argv[k]);
            if (k + 1 < out_argc) putc(' ');
        }
        putc('\n');
    }
}

static void builtin_true(int argc, char **argv) {
    (void)argc; (void)argv;
}

static void builtin_false(int argc, char **argv) {
    (void)argc; (void)argv;
}

static void builtin_linus(int argc, char **argv) {
    (void)argc; (void)argv;
    puts(CC "From:" C0 " torvalds@klaava.Helsinki.FI (Linus Benedict Torvalds)\n");
    puts(CC "Newsgroups:" C0 " comp.os.minix\n");
    puts(CC "Subject:" C0 " What would you like to see most in minix?\n");
    puts(CC "Date:" C0 " 25 Aug 91 20:57:08 GMT\n\n");
    puts(CY "  Hello everybody out there using minix --\n\n" C0);
    puts("  I'm doing a (free) operating system (just a hobby, won't be\n");
    puts("  big and professional like gnu) for 386(486) AT clones. This has\n");
    puts("  been brewing since april, and is starting to get ready. I'd like\n");
    puts("  any feedback on things people like/dislike in minix, as my OS\n");
    puts("  resembles it somewhat (same physical layout of the file-system\n");
    puts("  (due to practical reasons) among other things).\n\n");
    puts("  I've currently ported bash(1.08) and gcc(1.40), and things seem\n");
    puts("  to work. This implies that I'll get something practical within a\n");
    puts("  few months, and I'd like to know what features most people would\n");
    puts("  want. Any suggestions are welcome, but I won't promise I'll\n");
    puts("  implement them :-)\n\n");
    puts(CY "                Linus (torvalds@kruuna.helsinki.fi)\n\n" C0);
    puts(CG "  PS." C0 " Yes -- it's free of any minix code, and it has a multi-\n");
    puts("      threaded fs. It is NOT portable (uses 386 task switching\n");
    puts("      etc), and it probably never will support anything other\n");
    puts("      than AT-harddisks, as that's all I have :-(.\n\n");
    puts(CM "  -- And here we are, three and a half decades later. It still runs.\n" C0);
}

static void builtin_clear_cmd(int argc, char **argv) { (void)argc; (void)argv; builtin_clear(); }
static void builtin_exit_cmd(int argc, char **argv) { (void)argc; (void)argv; builtin_exit(); }
static void builtin_reboot_cmd(int argc, char **argv) { (void)argc; (void)argv; builtin_reboot(); }
static void builtin_halt_cmd(int argc, char **argv) { (void)argc; (void)argv; builtin_halt(); }
static void builtin_sync_cmd(int argc, char **argv) { (void)argc; (void)argv; builtin_sync(); }
static void builtin_pwd_cmd(int argc, char **argv) { (void)argc; (void)argv; builtin_pwd(); }
static void builtin_help_cmd(int argc, char **argv) { (void)argc; (void)argv; builtin_help(); }
static void builtin_hello_cmd(int argc, char **argv) { (void)argc; (void)argv; builtin_hello(); }
static void builtin_whoami_cmd(int argc, char **argv) { (void)argc; (void)argv; builtin_whoami(); }
static void builtin_mount_cmd(int argc, char **argv) { (void)argc; (void)argv; builtin_mount(); }
static void builtin_df_cmd(int argc, char **argv) { (void)argc; (void)argv; builtin_df(); }
static void builtin_history_cmd(int argc, char **argv) { builtin_history(argc, argv); }

static int eq2(const char *s, char a, char b) { return s[0] == a && s[1] == b && s[2] == 0; }
static int eq3(const char *s, char a, char b, char c) { return s[0] == a && s[1] == b && s[2] == c && s[3] == 0; }
static int eq4(const char *s, char a, char b, char c, char d) { return s[0] == a && s[1] == b && s[2] == c && s[3] == d && s[4] == 0; }
static int eq5(const char *s, char a, char b, char c, char d, char e) { return s[0] == a && s[1] == b && s[2] == c && s[3] == d && s[4] == e && s[5] == 0; }
static int eq6(const char *s, char a, char b, char c, char d, char e, char f) { return s[0] == a && s[1] == b && s[2] == c && s[3] == d && s[4] == e && s[5] == f && s[6] == 0; }
static int eq7(const char *s, char a, char b, char c, char d, char e, char f, char g) { return s[0] == a && s[1] == b && s[2] == c && s[3] == d && s[4] == e && s[5] == f && s[6] == g && s[7] == 0; }

static int run_builtin(int argc, char **argv) {
    char *s = argv[0];
    if (eq5(s,'h','e','l','l','o')) { builtin_hello_cmd(argc, argv); return 1; }
    if (eq4(s,'h','e','l','p')) { builtin_help_cmd(argc, argv); return 1; }
    if (eq5(s,'c','l','e','a','r')) { builtin_clear_cmd(argc, argv); return 1; }
    if (eq4(s,'e','x','i','t')) { builtin_exit_cmd(argc, argv); return 1; }
    if (eq4(s,'s','y','n','c')) { builtin_sync_cmd(argc, argv); return 1; }
    if (eq4(s,'h','a','l','t')) { builtin_halt_cmd(argc, argv); return 1; }
    if (eq6(s,'r','e','b','o','o','t')) { builtin_reboot_cmd(argc, argv); return 1; }
    if (eq4(s,'e','c','h','o')) { builtin_echo(argc, argv); return 1; }
    if (eq2(s,'c','d')) { builtin_cd(argc, argv); return 1; }
    if (eq3(s,'p','w','d')) { builtin_pwd_cmd(argc, argv); return 1; }
    if (eq2(s,'l','s')) { builtin_ls(argc, argv); return 1; }
    if (eq3(s,'c','a','t')) { builtin_cat(argc, argv); return 1; }
    if (eq5(s,'m','k','d','i','r')) { builtin_mkdir(argc, argv); return 1; }
    if (eq5(s,'r','m','d','i','r')) { builtin_rmdir(argc, argv); return 1; }
    if (eq2(s,'r','m')) { builtin_rm(argc, argv); return 1; }
    if (eq5(s,'t','o','u','c','h')) { builtin_touch(argc, argv); return 1; }
    if (eq2(s,'c','p')) { builtin_cp(argc, argv); return 1; }
    if (eq2(s,'m','v')) { builtin_mv(argc, argv); return 1; }
    if (eq2(s,'l','n')) { builtin_ln(argc, argv); return 1; }
    if (eq4(s,'h','e','a','d')) { builtin_head(argc, argv); return 1; }
    if (eq2(s,'w','c')) { builtin_wc(argc, argv); return 1; }
    if (eq4(s,'g','r','e','p')) { builtin_grep(argc, argv); return 1; }
    if (eq6(s,'w','h','o','a','m','i')) { builtin_whoami_cmd(argc, argv); return 1; }
    if (eq5(s,'m','o','u','n','t')) { builtin_mount_cmd(argc, argv); return 1; }
    if (eq2(s,'d','f')) { builtin_df_cmd(argc, argv); return 1; }
    if (eq2(s,'p','s')) { builtin_ps(argc, argv); return 1; }
	if (eq5(s,'u','n','a','m','e')) { builtin_uname(argc, argv); return 1; }
	if (eq7(s,'h','i','s','t','o','r','y')) { builtin_history_cmd(argc, argv); return 1; }
	if (eq4(s,'d','a','t','e')) { builtin_date(argc, argv); return 1; }
	if (eq3(s,'c','a','l')) { builtin_cal(argc, argv); return 1; }
	if (eq6(s,'u','p','t','i','m','e')) { builtin_uptime(argc, argv); return 1; }
	if (eq7(s,'f','o','r','t','u','n','e')) { builtin_fortune(argc, argv); return 1; }
	if (eq3(s,'y','e','s')) { builtin_yes(argc, argv); return 1; }
	if (eq4(s,'t','r','u','e')) { builtin_true(argc, argv); return 1; }
	if (eq5(s,'f','a','l','s','e')) { builtin_false(argc, argv); return 1; }
	if (eq5(s,'l','i','n','u','s')) { builtin_linus(argc, argv); return 1; }
	return 0;
}

/* ── Main loop ────────────────────────────────────────────────
 * Keep the production shell in canonical mode until raw TTY input
 * is reliable across scripted bEMU input and the real console path. */
static void shell_loop(void) {
	int n;

	for (;;) {
		build_prompt();
		linelen = 0;
        cursor = 0;
        hist_pos = hist_count;
        tab_pressed = 0;
		yank_len = 0;
		line[0] = 0;
		puts(prompt);

		if (raw_active) {
			n = read_line_raw();
		} else {
			n = read(0, line, MAX_LINE - 1);
			if (n <= 0)
				continue;
			line[n] = 0;
			while (n > 0 && (line[n - 1] == '\n' || line[n - 1] == '\r'))
				line[--n] = 0;
		}
		linelen = n;
		cursor = linelen;
		execute();
	}
}

/* ── Entry point ────────────────────────────────────────────── */
int main(int argc, char **argv) {
	int motd_fd, motd_n, r;
	char motd_buf[1800];

	(void)argc;
	(void)argv;
	cwd[0] = '/';
	cwd[1] = 0;
	boot_time = time((long *)0);
	save_termios();
	set_raw_mode();

	motd_fd = open("/etc/motd", O_RDONLY);
	if (motd_fd >= 0) {
		motd_n = 0;
		while (motd_n < (int)sizeof(motd_buf) - 1) {
			r = read(motd_fd, motd_buf + motd_n, sizeof(motd_buf) - 1 - motd_n);
			if (r <= 0) break;
			motd_n += r;
		}
		close(motd_fd);
if (motd_n > 0) {
motd_buf[motd_n] = 0;
puts("\n");
puts(motd_buf);
}
	}
	puts("\033[0m\n linux 0.01 \033[37m\376\033[0m interactive shell\n\n");
	load_history();

	shell_loop();

	restore_termios();
	return 0;
}
