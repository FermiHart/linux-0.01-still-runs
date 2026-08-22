#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <inttypes.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
#include <unistd.h>
#include <fcntl.h>

#define MINIX_HEADER 32
#define GCC_HEADER 1024

static void die(const char *str)
{
	fprintf(stderr, "%s\n", str);
	exit(1);
}

static void usage(void)
{
	die("Usage: build boot system [> image]");
}

static uint32_t get_le32(const unsigned char *p)
{
	return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
	       ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static ssize_t read_retry(int fd, void *buf, size_t len)
{
	ssize_t n;
	do {
		n = read(fd, buf, len);
	} while (n < 0 && errno == EINTR);
	return n;
}

static int read_exact(int fd, unsigned char *buf, size_t len)
{
	size_t done = 0;
	ssize_t n;
	while (done < len) {
		n = read_retry(fd, buf + done, len - done);
		if (n < 0)
			return -1;
		if (n == 0)
			return 1;
		done += (size_t)n;
	}
	return 0;
}

static int write_all(int fd, const unsigned char *buf, size_t len)
{
	size_t done = 0;
	ssize_t n;
	while (done < len) {
		n = write(fd, buf + done, len - done);
		if (n > 0) {
			done += (size_t)n;
			continue;
		}
		if (n < 0 && errno == EINTR)
			continue;
		if (n == 0)
			errno = EIO;
		return -1;
	}
	return 0;
}

int main(int argc, char **argv)
{
	int id, status;
	ssize_t count;
	size_t boot_size;
	uint64_t total;
	unsigned char buf[1024];

	if (argc != 3)
		usage();
	memset(buf, 0, sizeof(buf));
	if ((id = open(argv[1], O_RDONLY, 0)) < 0)
		die("Unable to open 'boot'");
	status = read_exact(id, buf, MINIX_HEADER);
	if (status < 0)
		die("Read error in header of 'boot'");
	if (status > 0)
		die("Unable to read header of 'boot'");
	if (get_le32(buf + 0) != UINT32_C(0x04100301))
		die("Non-Minix header of 'boot'");
	if (get_le32(buf + 4) != MINIX_HEADER)
		die("Non-Minix header of 'boot'");
	if (get_le32(buf + 12) != 0)
		die("Illegal data segment in 'boot'");
	if (get_le32(buf + 16) != 0)
		die("Illegal bss in 'boot'");
	if (get_le32(buf + 20) != 0)
		die("Non-Minix header of 'boot'");
	if (get_le32(buf + 28) != 0)
		die("Illegal symbol table in 'boot'");
	memset(buf, 0, sizeof(buf));
	boot_size = 0;
	for (;;) {
		count = read_retry(id, buf + boot_size, sizeof(buf) - boot_size);
		if (count < 0)
			die("Read error in 'boot'");
		if (count == 0)
			break;
		boot_size += (size_t)count;
		if (boot_size > 510)
			break;
	}
	fprintf(stderr, "Boot sector %zu bytes.\n", boot_size);
	if (boot_size > 510)
		die("Boot block may not exceed 510 bytes");
	buf[510] = 0x55;
	buf[511] = 0xAA;
	if (write_all(STDOUT_FILENO, buf, 512) < 0)
		die("Write call failed");
	if (close(id) < 0)
		die("Close of 'boot' failed");

	if ((id = open(argv[2], O_RDONLY, 0)) < 0)
		die("Unable to open 'system'");
	status = read_exact(id, buf, GCC_HEADER);
	if (status < 0)
		die("Read error in header of 'system'");
	if (status > 0)
		die("Unable to read header of 'system'");
	if (get_le32(buf + 20) != 0)
		die("Non-GCC header of 'system'");
	total = 0;
	for (;;) {
		count = read_retry(id, buf, sizeof(buf));
		if (count < 0)
			die("Read error in 'system'");
		if (count == 0)
			break;
		if (write_all(STDOUT_FILENO, buf, (size_t)count) < 0)
			die("Write call failed");
		if ((uint64_t)count > UINT64_MAX - total)
			die("System size overflow");
		total += (uint64_t)count;
	}
	if (close(id) < 0)
		die("Close of 'system' failed");
	fprintf(stderr, "System %" PRIu64 " bytes.\n", total);
	return 0;
}
