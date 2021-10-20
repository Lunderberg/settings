#!/usr/bin/env python3

"""Test availability of required packages."""

import argparse
from pathlib import Path
import sys

import pkg_resources


def main(args):
    with open(args.requirement) as f:
        requirements = list(pkg_resources.parse_requirements(f))

    num_errors = 0
    for requirement in requirements:
        try:
            pkg_resources.require(str(requirement))
        except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict) as e:
            print(e.report())
            num_errors += 1
    sys.exit(num_errors)


def arg_main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--requirement", type=Path, required=True)
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
