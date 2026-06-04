#!/usr/bin/env python3
"""QEMU shell smoke tests for linux-0.01-still-runs."""

import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time


KEYS = {
    " ": "spc",
    "/": "slash",
    ".": "dot",
    "-": "minus",
    "+": "plus",
    ">": "shift-dot",
    ";": "semicolon",
}


COMMANDS = [
    ("hello", ["Hello from C userland"], []),
    ("/bin/hello", ["Hello from C userland"], []),
    ("help", ["built-in commands"], []),
    ("echo oi", ["oi"], []),
    ("nope", ["nope: not found"], []),
    ("uname", ["linux .0"], []),
    ("uname -a", ["nodename", "machine"], []),
    ("history", ["hello"], []),
    ("ls", ["bin", "etc", "home", "tmp"], []),
    ("ls -la", ["drwx", "tmp"], []),
    ("ls -la /dev", ["tty0"], []),
    ("ls -la bin", ["shell", "hello"], []),
    ("whoami", ["root"], []),
    ("mount", ["/dev/hd1 on / type minix"], []),
    ("df", ["Filesystem", "/dev/hd1"], []),
    ("ps aux", ["USER  PID   PPID  STAT  TTY    TIME  COMMAND", "shell"], []),
    ("cat /etc/fstab", ["/dev/hd1 / minix rw"], []),
    ("cat /etc/motd", ["There is a specific feeling", "Welcome to 1991"], []),
    ("cd etc", ["fermihart@linux01:/etc$"], []),
    ("pwd", ["/etc"], []),
    ("cd ..", ["fermihart@linux01:/$"], []),
    ("pwd", ["/"], []),
    ("cd", ["fermihart@linux01:/home/fermihart$"], []),
    ("pwd", ["/home/fermihart"], []),
    ("ls", ["fermihart@linux01:/home/fermihart$"], [], ["bin  dev  etc"]),
    ("ls -la", [".", ".."], [], ["README", "motd"]),
    ("cd /", ["fermihart@linux01:/$"], []),
    ("cd tmp", ["fermihart@linux01:/tmp$"], []),
    ("mkdir core", [], []),
    ("cd core", ["fermihart@linux01:/tmp/core$"], []),
    ("pwd", ["/tmp/core"], []),
    ("touch empty", [], []),
    ("ls", ["empty"], []),
    ("echo alpha beta > a", [], []),
    ("cp a b", [], []),
    ("cat b", ["alpha beta"], []),
    ("mv b c", [], []),
    ("cat c", ["alpha beta"], []),
    ("ln c hard", [], []),
    ("rm c", [], []),
    ("cat hard", ["alpha beta"], []),
    ("head hard", ["alpha beta"], []),
    ("wc hard", ["1 2 11"], []),
    ("grep beta hard", ["alpha beta"], []),
    ("cd ..", ["fermihart@linux01:/tmp$"], []),
    ("rmdir core", [], []),
    ("cd /", ["fermihart@linux01:/$"], []),
    ("date", [":"], []),
    ("cal", ["Su Mo Tu We Th Fr Sa"], []),
    ("uptime", ["load average"], []),
    ("fortune", ["--"], []),
    ("true", [], []),
    ("false", [], []),
    ("linus", ["comp.os.minix"], []),
]

INTERACTIVE = [
    ("tab-complete whoami", ["w", "h", "o", "tab", "ret"], ["root"]),
    ("tab-complete /etc/motd", ["c", "a", "t", "spc", "slash", "e", "t", "c", "slash", "m", "tab", "ret"], ["There is a specific feeling"]),
    ("tab-complete path", ["c", "a", "t", "spc", "slash", "e", "t", "c", "slash", "f", "tab", "ret"], ["/dev/hd1 / minix rw"]),
    ("history up", ["e", "c", "h", "o", "spc", "h", "i", "s", "t", "ret", "up", "ret"], ["hist"]),
    ("ctrl-u", ["n", "o", "i", "s", "e", "ctrl-u", "e", "c", "h", "o", "spc", "c", "l", "e", "a", "n", "ret"], ["clean"]),
    ("left-insert", ["e", "c", "h", "o", "spc", "a", "c", "left", "b", "ret"], ["abc"]),
    ("ctrl-a-e", ["z", "z", "ctrl-a", "e", "c", "h", "o", "spc", "ctrl-e", "ret"], ["zz"]),
    ("ctrl-k", ["e", "c", "h", "o", "spc", "k", "e", "e", "p", "t", "r", "a", "s", "h", "left", "left", "left", "left", "left", "ctrl-k", "ret"], ["keep"]),
    ("ctrl-w", ["e", "c", "h", "o", "spc", "d", "r", "o", "p", "spc", "w", "o", "r", "d", "ctrl-w", "ret"], ["drop"]),
    ("ctrl-y", ["e", "c", "h", "o", "spc", "y", "a", "n", "k", "ctrl-w", "ctrl-y", "ret"], ["yank"]),
]


def parse_args():
    p = argparse.ArgumentParser(description="Linux 0.01 shell smoke tests")
    p.add_argument("--iso", default="build/linux-0.01.iso")
    p.add_argument("--img", default="build/root.img")
    p.add_argument("--qemu", default="qemu-system-i386")
    p.add_argument("--timeout", type=int, default=45)
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--interactive", action="store_true", help="also run timing-sensitive line editor tests")
    return p.parse_args()


def read_file(path):
    try:
        with open(path, "rb") as f:
            return f.read().decode("ascii", errors="replace")
    except FileNotFoundError:
        return ""


def clean(text):
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
    return text.replace("\r", "")


def has_crash(serial_log, qemu_log):
    serial = read_file(serial_log)
    qlog = read_file(qemu_log)
    crash_words = ("Kernel panic", "PANIC", "Triple Fault", "CPU Reset")
    return any(word in serial or word in qlog for word in crash_words)


def wait_for(path, needle, deadline):
    while time.time() < deadline:
        content = clean(read_file(path))
        if needle in content:
            return content
        time.sleep(0.1)
    return clean(read_file(path))


def wait_for_new_prompt(path, previous_len, deadline):
    while time.time() < deadline:
        raw = read_file(path)
        content = clean(raw)
        if len(content) > previous_len and "fermihart@linux01:/$" in content[previous_len:]:
            return content
        time.sleep(0.1)
    return clean(read_file(path))


def wait_for_command(path, previous_len, expected, deadline):
    while time.time() < deadline:
        raw = read_file(path)
        delta = clean(raw[previous_len:])
        has_prompt = "fermihart@linux01:" in delta and "$" in delta
        if expected and all(s in delta for s in expected) and has_prompt:
            return raw
        if not expected and has_prompt:
            return raw
        time.sleep(0.1)
    return read_file(path)


def wait_stable(path, deadline):
    last_len = -1
    stable = 0
    while time.time() < deadline:
        current_len = len(read_file(path))
        if current_len == last_len:
            stable += 1
            if stable >= 5:
                return current_len
        else:
            stable = 0
            last_len = current_len
        time.sleep(0.1)
    return len(read_file(path))


def hmp(sock, command):
    sock.settimeout(2)
    sock.sendall((command + "\n").encode("ascii"))
    data = b""
    deadline = time.time() + 2
    while time.time() < deadline:
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            break
        if not chunk:
            break
        data += chunk
        if b"(qemu)" in data:
            break
    return data.decode("ascii", "ignore")


def send_text(sock, text):
    for ch in text:
        if "a" <= ch <= "z" or "0" <= ch <= "9":
            key = ch
        elif "A" <= ch <= "Z":
            key = "shift-" + ch.lower()
        else:
            key = KEYS.get(ch)
        if not key:
            raise ValueError(f"no QEMU key mapping for {ch!r}")
        sock.sendall((f"sendkey {key}\n").encode("ascii"))
        time.sleep(0.025)
    sock.sendall(b"sendkey ret\n")


def send_keys(sock, keys):
    for key in keys:
        sock.sendall((f"sendkey {key}\n").encode("ascii"))
        time.sleep(0.08)


def launch(args, root_copy, serial_log, qemu_log, mon_sock):
    return subprocess.Popen([
        args.qemu,
        "-cdrom", args.iso,
        "-drive", f"file={root_copy},format=raw,if=none,id=hd0",
        "-device", "ide-hd,drive=hd0,bus=ide.0,unit=0,cyls=977,heads=5,secs=17",
        "-boot", "d",
        "-m", "8M",
        "-no-reboot",
        "-nographic",
        "-display", "none",
        "-serial", f"file:{serial_log}",
        "-monitor", f"unix:{mon_sock},server,nowait",
        "-d", "guest_errors,int",
        "-D", qemu_log,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    args = parse_args()
    if not os.path.exists(args.iso) or not os.path.exists(args.img):
        print("missing build artifacts; run make all first")
        return 1
    with tempfile.TemporaryDirectory(prefix="linux001-shell-") as td:
        serial_log = os.path.join(td, "serial.log")
        qemu_log = os.path.join(td, "qemu.log")
        mon_sock = os.path.join(td, "monitor.sock")
        root_copy = os.path.join(td, "root.img")
        shutil.copyfile(args.img, root_copy)
        proc = launch(args, root_copy, serial_log, qemu_log, mon_sock)
        boot_deadline = time.time() + args.timeout
        try:
            while time.time() < boot_deadline and not os.path.exists(mon_sock):
                time.sleep(0.05)
            mon = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            mon.settimeout(0.5)
            mon.connect(mon_sock)
            hmp(mon, "")
            content = wait_for(serial_log, "fermihart@linux01:/$", boot_deadline)
            if "fermihart@linux01:/$" not in content:
                print("shell prompt not reached")
                if args.verbose:
                    print(content[-2000:])
                return 1
            print("Starting shell smoke tests...")
            previous_len = wait_stable(serial_log, time.time() + 5)
            hmp(mon, "sendkey ret")
            content = wait_for_command(serial_log, previous_len, [], time.time() + 5)
            previous_len = wait_stable(serial_log, time.time() + 8)
            for item in COMMANDS:
                command, expected, raw_expected = item[:3]
                forbidden = item[3] if len(item) > 3 else []
                if args.verbose:
                    print(f"  {command}", flush=True)
                send_text(mon, command)
                time.sleep(0.3)
                if not expected and not raw_expected:
                    time.sleep(0.5)
                command_deadline = time.time() + 12
                content = wait_for_command(serial_log, previous_len, expected, command_deadline)
                raw_delta = content[previous_len:]
                delta = clean(content[previous_len:])
                if command == "cd tmp":
                    missing_now = [s for s in expected if s not in delta]
                    if missing_now:
                        time.sleep(2)
                        content = read_file(serial_log)
                        raw_delta = content[previous_len:]
                        delta = clean(content[previous_len:])
                previous_len = len(read_file(serial_log))
                missing = [s for s in expected if s not in delta]
                raw_missing = [s for s in raw_expected if s not in raw_delta]
                present_forbidden = [s for s in forbidden if s in delta]
                if has_crash(serial_log, qemu_log):
                    print(f"  {command}: kernel panic")
                    if args.verbose:
                        print(content[-3000:])
                    return 1
                if missing:
                    print(f"  {command}: missing {missing}")
                    if args.verbose:
                        print(delta[-2000:])
                    return 1
                if raw_missing:
                    print(f"  {command}: missing raw {raw_missing}")
                    if args.verbose:
                        print(repr(raw_delta[-2000:]))
                    return 1
                if present_forbidden:
                    print(f"  {command}: unexpected {present_forbidden}")
                    if args.verbose:
                        print(delta[-2000:])
                    return 1
                print(f"  {command}")
                previous_len = wait_stable(serial_log, time.time() + 5)
            if not args.interactive:
                return 0
            for name, keys, expected in INTERACTIVE:
                if args.verbose:
                    print(f"  {name}", flush=True)
                send_keys(mon, keys)
                content = wait_for_command(serial_log, previous_len, expected, time.time() + 8)
                delta = clean(content[previous_len:])
                previous_len = len(content)
                missing = [s for s in expected if s not in delta]
                if has_crash(serial_log, qemu_log):
                    print(f"  {name}: kernel panic")
                    if args.verbose:
                        print(content[-3000:])
                    return 1
                if missing:
                    print(f"  {name}: missing {missing}")
                    if args.verbose:
                        print(delta[-2000:])
                    return 1
                print(f"  {name}")
                previous_len = wait_stable(serial_log, time.time() + 3)
            return 0
        finally:
            proc.kill()
            proc.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
