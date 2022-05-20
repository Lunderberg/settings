#!/usr/bin/env python3

"""
Wrappers for adding an exception handler around

Usage:

from debug_utils import ExceptDebug
with ExceptDebug:
    pass

from debug_utils import ExceptDebug
@ExceptDebug
def failing_function():
    pass
"""

import functools
import sys
import traceback

try:
    import ipdb as pdb
except ImportError:
    import pdb


class _ExceptDebugImpl:
    def __call__(self, function):
        @functools.wraps(function)
        def inner(*args, **kwargs):
            with self:
                return function(*args, **kwargs)

        return inner

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is None:
            return

        traceback.print_exc()

        if sys.stdout.isatty():
            pdb.post_mortem()


ExceptDebug = _ExceptDebugImpl()
