#!/usr/bin/env python3
"""Quick single-command QEMU test. Usage:
  python3 tests/qquick.py "ls /" --expect "bin"
  python3 tests/qquick.py "nope" --expect "not found"
  python3 tests/qquick.py "pwd" --expect "/"
"""
import argparse, os, re, shutil, socket, subprocess, sys, tempfile, time

KEYS = {" ":"spc","/":"slash",".":"dot","-":"minus","+":"plus",">":"shift-dot",";":"semicolon"}

def clean(t):
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]","",t).replace("\r","")

def read_file(p):
    try:
        with open(p,"r",errors="ignore") as f: return f.read()
    except: return ""

def wait_stable(path, timeout=3):
    last, stable = -1, 0
    dl = time.time() + timeout
    while time.time() < dl:
        cur = len(read_file(path))
        if cur == last: stable += 1
        else: stable = 0
        last = cur
        if stable >= 5: return cur
        time.sleep(0.1)
    return len(read_file(path))

def main():
    p = argparse.ArgumentParser()
    p.add_argument("command")
    p.add_argument("--expect", required=True)
    p.add_argument("--iso", default="build/linux-0.01.iso")
    p.add_argument("--img", default="build/root.img")
    p.add_argument("--setup", default="", help="commands to run before test cmd, separated by |")
    args = p.parse_args()

    td = tempfile.mkdtemp(prefix="qq-")
    serial = os.path.join(td, "serial.log")
    mon_sock = os.path.join(td, "mon.sock")
    root = os.path.join(td, "root.img")
    shutil.copyfile(args.img, root)

    proc = subprocess.Popen([
        "qemu-system-i386","-cdrom",args.iso,
        "-drive",f"file={root},format=raw,if=none,id=hd0",
        "-device","ide-hd,drive=hd0,bus=ide.0,unit=0,cyls=977,heads=5,secs=17",
        "-boot","d","-m","8M","-no-reboot","-nographic","-display","none",
        "-serial",f"file:{serial}","-monitor",f"unix:{mon_sock},server,nowait",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        dl = time.time() + 30
        while time.time() < dl and not os.path.exists(mon_sock):
            time.sleep(0.05)
        mon = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        mon.settimeout(0.5)
        mon.connect(mon_sock)
        mon.sendall(b"\n")

        dl = time.time() + 30
        while time.time() < dl:
            if "fermihart@linux01:" in clean(read_file(serial)):
                break
            time.sleep(0.2)

        wait_stable(serial, 3)

        def send(cmd):
            for ch in cmd:
                if "a"<=ch<="z" or "0"<=ch<="9": key=ch
                elif "A"<=ch<="Z": key="shift-"+ch.lower()
                else: key=KEYS.get(ch)
                if not key: key=ch
                mon.sendall(f"sendkey {key}\n".encode())
                time.sleep(0.025)
            mon.sendall(b"sendkey ret\n")

        if args.setup:
            for cmd in args.setup.split("|"):
                send(cmd.strip())
                time.sleep(1)
                wait_stable(serial, 2)

        prev = len(read_file(serial))
        send(args.command)

        dl = time.time() + 8
        while time.time() < dl:
            raw = read_file(serial)
            delta = clean(raw[prev:])
            if args.expect in delta and "fermihart@linux01:" in delta and "$" in delta:
                print(f"OK: '{args.expect}' found")
                return 0
            time.sleep(0.1)

        raw = read_file(serial)
        delta = clean(raw[prev:])
        if args.expect in delta:
            print(f"OK: '{args.expect}' found (prompt delayed)")
            return 0

        print(f"FAIL: '{args.expect}' NOT found in output:")
        print(delta[-500:])
        return 1
    finally:
        proc.kill()
        proc.wait(timeout=5)

if __name__=="__main__": sys.exit(main())
