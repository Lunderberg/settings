#!/usr/bin/env python3

import argparse
import subprocess


def get_default_gateway():
    res = subprocess.check_output(["ip", "route", "list"], encoding="utf-8")
    for line in res.split("\n"):
        if line.startswith("default via"):
            return line.split()[2]
    else:
        raise RuntimeError("Couldn't find default gateway in output of `ip route list`")


def get_mac_address(ip_address):
    res = subprocess.check_output(["ip", "neigh", "show", ip_address], encoding="utf-8")
    items = res.split()
    if "lladdr" in items:
        return items[items.index("lladdr") + 1]
    else:
        raise RuntimeError(f"No entry in `ip neigh show` for {ip_address}")


def main(args):
    default_gateway = get_default_gateway()
    mac_address = get_mac_address(default_gateway)
    print(mac_address)


def arg_main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pdb",
        action="store_true",
        help="Start a pdb post mortem on uncaught exception",
    )

    args = parser.parse_args()

    try:
        main(args)
    except Exception:
        if args.pdb:
            import pdb, traceback

            traceback.print_exc()
            pdb.post_mortem()
        raise


if __name__ == "__main__":
    arg_main()
