#!/usr/bin/env python3

import argparse
import datetime
import pathlib
import re
import subprocess
import time


def initialize(path):
    if path.joinpath(".git").exists():
        return

    subprocess.check_call(["git", "init"], cwd=path)


def set_up_git_ignore(path):
    to_ignore = ["*.FCStd1"]
    gitignore = path.joinpath(".gitignore").resolve()

    if gitignore.exists():
        with gitignore.open("r") as f:
            ignored = set(line.strip() for line in f.readlines())
        to_ignore = [pattern for pattern in to_ignore if pattern not in ignored]

    if not to_ignore:
        return

    with gitignore.open("a") as f:
        for pattern in to_ignore:
            f.write(f"{pattern}\n")

    subprocess.check_call(["git", "add", "--", str(gitignore)], cwd=path)
    subprocess.check_call(
        ["git", "commit", "--message", "Added .gitignore", "--", str(gitignore)],
        cwd=path,
    )


def has_untracked_files(path):
    text = subprocess.check_output(
        ["git", "ls-files", "--other", "--exclude-standard"],
        cwd=path,
    )
    return bool(text.strip())


def has_modified_files(path):
    proc = subprocess.run(
        ["git", "diff", "--quiet"],
        cwd=path,
    )
    return bool(proc.returncode)


def incremental_commit(path):
    print("Incremental commit at ", datetime.datetime.now())
    needs_commit = has_untracked_files(path) or has_modified_files(path)
    if not needs_commit:
        return

    subprocess.check_call(["git", "add", "--", str(path)], cwd=path)
    subprocess.check_call(
        ["git", "commit", "--message", "Incremental commit"],
        cwd=path,
    )


def main(args):
    path = args.path.resolve()
    assert path.exists(), f"Watched path must exist, {path} does not."
    assert path.is_dir(), f"Watched path must be a directory, {path} is not."

    initialize(path)
    set_up_git_ignore(path)

    proc = None
    if args.command:
        proc = subprocess.Popen(args.command)

    def sleep():
        if proc:
            sleep_until = datetime.datetime.now() + args.time_between_updates
            while datetime.datetime.now() < sleep_until:
                if proc.poll() is not None:
                    return
                time.sleep(1.0)
        else:
            time.sleep(args.time_between_updates.total_seconds())

    while proc is None or proc.poll() is None:
        incremental_commit(path)

        try:
            sleep()
        except KeyboardInterrupt:
            break

    incremental_commit(path)


def arg_main():
    def parse_timedelta(s):
        res = re.match(
            (
                # fmt: off
                r"((?P<hours>\d+)h)?"
                r"\s*"
                r"((?P<minutes>\d+)m)?"
                r"\s*"
                r"((?P<seconds>\d+)s)?"
                # fmt: on
            ),
            s,
        )
        assert res

        def to_int(name):
            name = res.group(name)
            if name is None:
                return 0
            else:
                return int(name, base=10)

        return datetime.timedelta(
            hours=to_int("hours"),
            minutes=to_int("minutes"),
            seconds=to_int("seconds"),
        )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--path",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help=(
            "The path to be periodically backed up.  "
            "If unspecified, use the current directory."
        ),
    )
    parser.add_argument(
        "-t",
        "--time-between-updates",
        type=parse_timedelta,
        default=datetime.timedelta(minutes=30),
        help=("The time between checks for incremental updates."),
    )
    parser.add_argument(
        "--pdb",
        action="store_true",
        help="Start a pdb post mortem on uncaught exception",
    )
    parser.add_argument(
        "command",
        nargs="+",
        default=None,
        type=str,
        help=(
            "Command to run as a subprocess.  "
            "When the command terminates, "
            "stop watching for incremental updates.  "
            "If unset, watch until terminated."
        ),
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
