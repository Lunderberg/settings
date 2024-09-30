#!/usr/bin/env python3


import ctypes
import glob
import json
import io
import itertools
import math
import os
import pathlib
import re
import struct
import textwrap
import typing
from typing import Callable, Dict, List, Optional, Union, Iterable, Iterator

# Safetensor names are defined by their enum name in the Rust
# implementation at
# https://github.com/huggingface/safetensors/blob/main/safetensors/src/tensor.rs#L635
BYTES_PER_ELEMENT = {
    # Boolean values are stored as c-style addressable booleans, with
    # 1 value per byte.  They are not packed into 8 values per byte.
    #
    # https://github.com/huggingface/safetensors/blob/main/safetensors/src/tensor.rs#L679
    "BOOL": 1,
    "U8": 1,
    "I8": 1,
    # FP8 <https://arxiv.org/pdf/2209.05433.pdf>_
    "F8_E5M2": 1,
    # FP8 <https://arxiv.org/pdf/2209.05433.pdf>_
    "F8_E4M3": 1,
    "I16": 2,
    "U16": 2,
    "F16": 2,
    "BF16": 2,
    "I32": 4,
    "U32": 4,
    "F32": 4,
    "F64": 8,
    "I64": 8,
    "U64": 8,
}

SAFETENSOR_DTYPE_TO_NUMPY = {
    # Boolean values are stored as c-style addressable booleans, with
    # 1 value per byte.  They are not packed into 8 values per byte.
    #
    # https://github.com/huggingface/safetensors/blob/main/safetensors/src/tensor.rs#L679
    "BOOL": "bool",
    "U8": "uint8",
    "I8": "int8",
    # FP8 <https://arxiv.org/pdf/2209.05433.pdf>_
    "F8_E5M2": "float8",
    # FP8 <https://arxiv.org/pdf/2209.05433.pdf>_
    "F8_E4M3": "float8",
    "I16": "int16",
    "U16": "uint16",
    "F16": "float16",
    "BF16": "bfloat16",
    "I32": "int32",
    "U32": "uint32",
    "F32": "float32",
    "F64": "float64",
    "I64": "int64",
    "U64": "uint64",
}


class _GlobMixIn:
    def glob(self, pattern: str) -> List["LazySafetensor"]:
        regex = glob.fnmatch.translate(pattern)
        return list(self.regex(regex))

    def regex(self, regex: str) -> Iterator["LazySafetensor"]:
        for name, tensor in self.items():
            if re.match(regex, name):
                yield tensor


class _OrderedIndexMixIn:
    def __init_subclass__(cls):
        old_getitem = cls.__getitem__

        def __getitem__(self, index_or_name: Union[int, str]) -> "LazySafetensor":
            if isinstance(index_or_name, int):
                # Relies on python 3.7+ providing a guarantee that
                # dictionaries will be ordered.
                values = self.values()
                try:
                    for _ in range(index_or_name):
                        next(values)
                    return next(values)
                except StopIteration:
                    raise IndexError("list index out of range")

            elif isinstance(index_or_name, slice):
                return list(
                    itertools.islice(
                        self.values(),
                        index_or_name.start,
                        index_or_name.stop,
                        index_or_name.step,
                    )
                )

            else:
                return old_getitem(self, index_or_name)

        cls.__getitem__ = __getitem__


class LazySafetensorCollection(_GlobMixIn, _OrderedIndexMixIn):
    def __init__(
        self,
        *safetensor_files: Iterable[Union[str, pathlib.Path, "LazySafetensorFile"]],
    ):
        self._safetensor_files = [
            safetensor_file
            for file_or_path in safetensor_files
            for safetensor_file in self._normalize_file(file_or_path)
        ]

    @classmethod
    def _normalize_file(
        cls,
        safetensor_file: Union[str, pathlib.Path, "LazySafetensorFile"],
    ) -> Iterator["LazySafeTensorFile"]:
        if isinstance(safetensor_file, str):
            safetensor_file = pathlib.Path(safetensor_file)

        if isinstance(safetensor_file, LazySafetensorFile):
            yield safetensor_file
        elif safetensor_file.is_dir():
            for filepath in sorted(safetensor_file.glob("*.safetensors")):
                yield LazySafetensorFile(filepath)
        else:
            yield LazySafetensorFile(safetensor_file)

    @property
    def _file_lookup(self):
        if not hasattr(self, "_file_lookup_cache"):
            self._file_lookup_cache = {
                name: file for file in self._safetensor_files for name in file.tensors
            }

        return self._file_lookup_cache

    def __len__(self) -> int:
        return len(self._file_lookup)

    def __getitem__(self, name) -> "LazySafetensor":
        return self._file_lookup[name][name]

    def __contains__(self, name):
        return name in self._file_lookup

    def __iter__(self):
        return iter(self.keys())

    def keys(self):
        return self._file_lookup.keys()

    def values(self):
        for key in self.keys():
            yield self[key]

    def items(self):
        for key in self.keys():
            yield key, self[key]

    def num_files(self) -> int:
        return len(self._safetensor_files)


class LazySafetensorDir(LazySafetensorCollection):
    def __init__(self, dirpath: Union[str, pathlib.Path]):
        self.dirpath = pathlib.Path(dirpath)
        super().__init__(self.dirpath)


class LazySafetensorFile(_GlobMixIn, _OrderedIndexMixIn):
    def __init__(self, filepath: Union[str, pathlib.Path]):
        filepath = pathlib.Path(filepath)
        self.filepath = filepath
        self._handle = self.filepath.open("rb")
        self._tensors: Optional[Dict[str, "LazySafetensor"]] = None

    @property
    def tensors(self) -> Dict[str, "LazySafetensor"]:
        if self._tensors is not None:
            return self._tensors

        self._handle.seek(0, os.SEEK_END)
        file_size_bytes = self._handle.tell()
        self._handle.seek(0, os.SEEK_SET)

        # A uint64 header
        json_header_nbytes = struct.unpack("<Q", self._handle.read(8))[0]
        # Followed by that many bytes as a JSON packet
        json_header = self._handle.read(json_header_nbytes)
        header = json.loads(json_header)

        def _try_int(value):
            try:
                return int(value)
            except ValueError:
                return value

        def _sort_key(item):
            name, _value = item
            return tuple(_try_int(s) for s in name.split("."))

        items = sorted(header.items(), key=_sort_key)

        tensors = {}
        for name, entry in items:
            if name != "__metadata__":
                dtype = entry["dtype"]
                shape = entry["shape"]

                # The data_offset is relative to the end of the JSON header,
                # *NOT* to the file itself.
                data_offsets = [
                    offset + json_header_nbytes + 8 for offset in entry["data_offsets"]
                ]

                assert len(data_offsets) == 2
                assert data_offsets[0] <= data_offsets[1] <= file_size_bytes

                nbytes = data_offsets[1] - data_offsets[0]
                expected_nbytes = math.prod(shape) * BYTES_PER_ELEMENT[dtype]

                assert nbytes == expected_nbytes

                tensors[name] = LazySafetensor(
                    self._handle,
                    name,
                    dtype=dtype,
                    shape=shape,
                    data_offset_in_file=data_offsets[0],
                )

        self._tensors = tensors
        return self._tensors

    def __len__(self) -> int:
        return len(self.tensors)

    def __getitem__(self, name: str) -> "LazySafetensor":
        return self.tensors[name]

    def __contains__(self, name: str) -> bool:
        return name in self.tensors

    def __iter__(self):
        return iter(self.keys())

    def keys(self):
        return self.tensors.keys()

    def values(self):
        return self.tensors.values()

    def items(self):
        return self.tensors.items()


class LazySafetensor:
    def __init__(
        self,
        file_handle: typing.IO[bytes],
        name: str,
        dtype: str,
        shape: List[int],
        data_offset_in_file: int,
    ):
        self.file_handle = file_handle
        self.name = name
        self.dtype = dtype
        self.shape = shape
        self.data_offset_in_file = data_offset_in_file

    def __repr__(self):
        dtype = SAFETENSOR_DTYPE_TO_NUMPY[self.dtype]
        return f"LazySafetensor('{dtype}', {self.shape}, '{self.name}')"

    @property
    def bytes_per_element(self) -> int:
        return BYTES_PER_ELEMENT[self.dtype]

    @property
    def num_bytes(self) -> int:
        return self.num_elements * self.bytes_per_element

    @property
    def num_elements(self) -> int:
        return int(math.prod(self.shape))

    def numpy(self) -> "np.ndarray":
        import numpy as np

        dtype = SAFETENSOR_DTYPE_TO_NUMPY[self.dtype]
        self.file_handle.seek(self.data_offset_in_file)
        arr = np.fromfile(self.file_handle, dtype=dtype, count=self.num_elements)
        arr = arr.reshape(self.shape)

        return arr

    def torch(self) -> "torch.array":
        import torch

        # Because pytorch does not provide any string to dtype
        # conversions.  It would be really, really useful if they did.
        dtype = {
            "BOOL": torch.bool,
            "U8": torch.uint8,
            "I8": torch.int8,
            "F8_E5M2": torch.float8_e5m2,
            "F8_E4M3": torch.float8_e4m3fn,
            "I16": torch.int16,
            "U16": torch.uint16,
            "F16": torch.float16,
            "BF16": torch.bfloat16,
            "I32": torch.int32,
            "U32": torch.uint32,
            "F32": torch.float32,
            "F64": torch.float64,
            "I64": torch.int64,
            "U64": torch.uint64,
        }[self.dtype]

        # Pytorch cannot load a tensor from a file handle
        # (`torch.from_file` requires a path to a file).  Need to read
        # the bytes, then make a `BytesIO` object, and then return a
        # readable/writable view into the `BytesIO`.
        #
        # If pytorch does add support for a file handle in
        # `torch.from_file`, must ensure that `shared=False` is
        # provided.  Otherwise, pytorch will attempt to write any
        # changes back to the original file.
        self.file_handle.seek(self.data_offset_in_file)
        tensor_bytes = io.BytesIO(self.file_handle.read(self.num_bytes))
        rw_buffer = tensor_bytes.getbuffer()

        arr = torch.frombuffer(
            rw_buffer,
            dtype=dtype,
            count=self.num_elements,
        )
        arr = arr.reshape(self.shape)

        return arr


def main(args):
    safetensors = LazySafetensorCollection(*args.safetensor_files)

    if not args.quiet:
        print(
            "Found {num_tensors} {tensor_noun} in {num_files} {file_noun}".format(
                num_tensors=len(safetensors),
                tensor_noun="tensor" if len(safetensors) == 1 else "tensors",
                num_files=safetensors.num_files(),
                file_noun="file" if safetensors.num_files() == 1 else "files",
            )
        )

        print(
            textwrap.dedent(
                """
                Tensors may be inspected through the `safetensors` object.

                Examples:

                    # Print first three tensors
                    print(safetensors[:3])

                    # Print all tensors from layer 5
                    print(safetensors.glob('*.layers.5.*'))

                    # Print a specific tensor by name
                    print(safetensors['model.lm_head.weight'])

                (Pass the -q or --quiet flag to disable this startup message.)
                """
            ).lstrip()
        )

    try:
        __import__("IPython").embed(colors="neutral")
    except ImportError:
        __import__("code").interact(local=locals())


def arg_main():
    import argparse
    import contextlib
    import sys

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

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "safetensor_files",
        type=pathlib.Path,
        default=[pathlib.Path(".")],
        nargs="*",
        help="The file or directory to inspect",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Silence the startup messages",
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
