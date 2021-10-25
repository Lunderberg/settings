#!/usr/bin/env python3

import argparse
import json
from pathlib import Path
import shlex


def find_lastfailed_file(path=None):
    if path is None:
        path = Path.cwd()

    while path != path.root:
        cache_dir = path / ".pytest_cache"
        if cache_dir.is_dir():
            return cache_dir.joinpath("v", "cache", "lastfailed")

    return None


def read_lastfailed_file(path):
    with open(path) as f:
        data = json.load(f)

    return list(data)


def dump_failing(failing):
    for item in failing:
        print(shlex.quote(item))


def main(args):
    path = find_lastfailed_file()
    failing = read_lastfailed_file(path)
    dump_failing(failing)


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
