#!/usr/bin/env python3

import argparse
import contextlib
import itertools
import pathlib
import sys

import torch
import safetensors.torch

from tqdm import tqdm


def main(args):
    input_dir = args.input_dir
    output_dir = args.output_dir

    if output_dir.exists():
        assert output_dir.is_dir()
    else:
        output_dir.mkdir(parents=True)

    pytorch_bins = sorted(
        itertools.chain(
            input_dir.glob("*.bin"),
            input_dir.glob("*.pth"),
        )
    )
    for pytorch_bin in tqdm(pytorch_bins):
        output_filepath = output_dir.joinpath(pytorch_bin.name).with_suffix(
            ".safetensors"
        )
        tensors = torch.load(pytorch_bin, map_location="cpu")
        safetensors.torch.save_file(tensors, output_filepath.as_posix())


@contextlib.contextmanager
def debug_on_except():
    try:
        yield
    finally:
        if isinstance(sys.exc_info()[1], Exception):
            import traceback

            try:
                import ipdb as pdb
            except ImportError:
                import pdb

            traceback.print_exc()
            pdb.post_mortem()


def arg_main():
    cwd = pathlib.Path.cwd()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pdb",
        action="store_true",
        help="Start a pdb post mortem on uncaught exception",
    )
    parser.add_argument(
        "--input-dir",
        type=pathlib.Path,
        default=cwd,
        help="The directory in which to search for pytorch files (*.pth or *.bin)",
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=cwd,
        help="The directory in which to generate *.safetensors files",
    )

    args = parser.parse_args()

    with contextlib.ExitStack() as stack:
        if args.pdb:
            stack.enter_context(debug_on_except())

        main(args)


if __name__ == "__main__":
    arg_main()
