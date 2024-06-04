#!/usr/bin/env python3

import argparse
import contextlib
import json
import pathlib
import sys

from collections import Counter
from typing import Iterator


import safetensors
import safetensors.torch
import torch
from tqdm import tqdm


class LazyTensor:
    def __init__(
        self,
        filepath: pathlib.Path,
        input_file: safetensors.safe_open,
        name: str,
    ):
        self.filepath = filepath
        self.input_file = input_file
        self.name = name

    def get(self):
        return self.input_file.get_tensor(self.name)


def iter_tensors(dirpath: pathlib.Path) -> Iterator[LazyTensor]:
    for filepath in sorted(dirpath.glob("*.safetensors")):
        safetensors_file = safetensors.safe_open(
            filepath.as_posix(), framework="pt", device="cpu"
        )
        for key in safetensors_file.keys():
            yield LazyTensor(filepath, safetensors_file, key)


def get_lora_names(name):
    name = name.split(".")
    assert name[-1] == "weight"

    lora_A_name = ".".join(["base_model", "model", *name[:-1], "lora_A", "weight"])
    lora_B_name = ".".join(["base_model", "model", *name[:-1], "lora_B", "weight"])

    return lora_A_name, lora_B_name


def main(args):
    lora_config_filepath = args.lora.joinpath("adapter_config.json")
    lora_config = json.load(lora_config_filepath.open())

    lora_scale_factor = lora_config["lora_alpha"] / lora_config["r"]

    base_weights = list(iter_tensors(args.base_weights))
    lora_weights = list(iter_tensors(args.lora))

    lora_name_counts = Counter(tensor.name for tensor in lora_weights)
    for name, count in lora_name_counts.items():
        assert count == 1, f"Multiple files contain LoRA tensor named '{name}'"

    lora_lookup = {tensor.name: tensor for tensor in lora_weights}
    assert len(lora_lookup) == len(lora_weights)

    valid_lora_names = set(
        lora_name
        for base_tensor in base_weights
        for lora_name in get_lora_names(base_tensor.name)
    )
    for lora_tensor in lora_weights:
        assert lora_tensor.name in valid_lora_names

    for base_tensor in base_weights:
        lora_A_name, lora_B_name = get_lora_names(base_tensor.name)
        if lora_A_name in lora_lookup:
            assert lora_B_name in lora_lookup
        if lora_B_name in lora_lookup:
            assert lora_A_name in lora_lookup

    assert len(list(args.output.glob("*.safetensors"))) == 0
    args.output.mkdir(parents=True, exist_ok=True)

    current_filepath = None
    current_contents = {}

    def flush_current_file():
        nonlocal current_filepath
        nonlocal current_contents

        if current_filepath is None:
            return

        output_filepath = args.output.joinpath(current_filepath.name)

        safetensors.torch.save_file(
            current_contents,
            output_filepath,
            metadata={"format": "pt"},
        )

        current_filepath = None
        current_contents = {}

    for lazy_tensor in tqdm(base_weights):
        if current_filepath and current_filepath != lazy_tensor.filepath:
            flush_current_file()

        tensor = lazy_tensor.get()

        lora_A_name, lora_B_name = get_lora_names(lazy_tensor.name)

        if lora_A_name in lora_lookup or lora_B_name in lora_lookup:
            assert lora_A_name in lora_lookup and lora_B_name in lora_lookup

            lora_A = lora_lookup[lora_A_name].get()
            lora_B = lora_lookup[lora_B_name].get()

            new_tensor = tensor + torch.matmul(lora_B, lora_A) * lora_scale_factor
            tensor = new_tensor

        current_filepath = lazy_tensor.filepath
        current_contents[lazy_tensor.name] = tensor

    flush_current_file()


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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-weights",
        type=pathlib.Path,
        help="Path to directory containing *.safetensors files for the base weights",
    )
    parser.add_argument(
        "--lora",
        type=pathlib.Path,
        help="Path to directory containing *.safetensors files for the LoRA",
    )
    parser.add_argument(
        "--max-file-gigabytes",
        type=float,
        help="The maximum size of each safetensors file",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        help="Path in which new *.safetensors files should be generated",
    )
    parser.add_argument(
        "--pdb",
        action="store_true",
        help="Start a pdb post mortem on uncaught exception",
    )

    args = parser.parse_args()

    with contextlib.ExitStack() as stack:
        if args.pdb:
            stack.enter_context(debug_on_except())

        main(args)


if __name__ == "__main__":
    arg_main()
