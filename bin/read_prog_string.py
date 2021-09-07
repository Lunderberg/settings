#!/usr/bin/env python3

"""Read a string from a running program's memory

Can be used for programs that are in uninterruptible sleep.
"""

import argparse
from collections import namedtuple
import contextlib
import re
from types import SimpleNamespace

import psutil

MemMapRegion = namedtuple(
    "MemMapRegion", ["address", "permissions", "offset", "device", "inode", "pathname"]
)


def read_map_line(line):
    line = line.split()
    if len(line) == 5:
        address, perms, offset, device, inode = line
        pathname = None
    elif len(line) == 6:
        address, perms, offset, device, inode, pathname = line

    address = address.split("-")
    assert len(address) == 2
    address = (int(address[0], base=16), int(address[1], base=16))

    perms = set(perms)
    perms.discard("-")

    name_map = {
        "r": "read",
        "w": "write",
        "x": "execute",
        "s": "shared",
        "p": "private",
    }
    for shortname, longname in name_map.items():
        if shortname in perms:
            perms.add(longname)

    return MemMapRegion(address, perms, offset, device, inode, pathname)


def mmap_regions(pid):
    with open(f"/proc/{pid}/maps", "r") as maps_file:
        for line in maps_file:
            region = read_map_line(line)
            # Not sure why, but I get an OSError from attempting to
            # read the [vvar] section.  Better to exclude it early.
            if region.pathname != "[vvar]":
                yield region


class RequiresPtraceScope:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        if exc_type == PermissionError:
            raise PermissionError(
                "Consider temporarily disabling ptrace_scope protections "
                "with 'echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope'"
            )


def open_proc_file(pid, proc_file):
    if proc_file in ["maps", "syscall"]:
        mode = "r"
        buffering = -1
    elif proc_file in ["mem"]:
        mode = "rb"
        buffering = 0

    if proc_file in ["mem", "syscall"]:
        context = RequiresPtraceScope()
    else:
        context = contextlib.nullcontext()

    with context:
        return open(f"/proc/{pid}/{proc_file}", mode, buffering)


def read_string_at(pid, address):
    for region in mmap_regions(pid):
        if region.address[0] <= address < region.address[1]:
            break
    else:
        raise RuntimeError(f"Address 0x{address:x} not found in /proc/{pid}/maps")

    bytes_remaining = region.address[1] - address
    chunk_size = 1024

    chunks = []
    with open_proc_file(pid, "mem") as mem_file:
        mem_file.seek(address)

        while bytes_remaining:
            chunk = mem_file.read(min(bytes_remaining, chunk_size))
            bytes_remaining -= len(chunk)
            if b"\0" in chunk:
                chunks.append(chunk.split(b"\0")[0])
                break
            else:
                chunks.append(chunk)

    return b"".join(chunks)


def run(args):
    if args.openat_path:
        args.address = read_openat_path(args.pid)

    print(read_string_at(args.pid, args.address).decode("utf-8"))


def parse_int_detect_base(s):
    return int(s, base=0)


def read_openat_path(pid):
    with RequiresPtraceScope(), open_proc_file(pid, "syscall") as f:
        text = f.read().strip()

    if text == "running":
        raise RuntimeError(f"PID {pid} is not currently in a syscall")

    values = text.split()
    syscall = int(values[0])

    if syscall != 257:
        raise RuntimeError(
            f"PID {pid} is currently in syscall {syscall}, not openat (257)"
        )

    address = int(values[2], base=16)

    return address


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p", "--pid", type=int, required=True, help="PID of the process to be checked"
    )
    parser.add_argument(
        "-a",
        "--address",
        type=parse_int_detect_base,
        help="Memory address of the string to read",
    )
    parser.add_argument(
        "--openat-path",
        action="store_true",
        help="Read memory address from currently active openat syscall",
    )
    parser.add_argument(
        "--pdb",
        action="store_true",
        help="Drop into pdb on exception",
    )
    args = parser.parse_args()

    if args.address is None and not args.openat_path:
        parser.error("Either --address or --openat-path is required")

    if args.pdb:
        try:
            run(args)
        except Exception:
            import pdb, traceback

            traceback.print_exc()
            pdb.post_mortem()
    else:
        run(args)


if __name__ == "__main__":
    main()
