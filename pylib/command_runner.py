#!/usr/bin/env python3

import collections
import os
import subprocess

from typing import Dict, Optional


# Adapted from https://stackoverflow.com/a/59903465
class PeekIterator:
    def __init__(self, iterable):
        self.iterator = iter(iterable)
        self.peeked = collections.deque()

    def __iter__(self):
        return self

    def __next__(self):
        if self.peeked:
            return self.peeked.popleft()
        return next(self.iterator)

    def has_next(self, ahead=0):
        self._extend(ahead)
        return ahead < len(self.peeked)

    def peek(self, ahead=0):
        self._extend(ahead)
        if ahead < len(self.peeked):
            return self.peeked[ahead]
        else:
            return None

    def _extend(self, ahead=0):
        while len(self.peeked) <= ahead:
            try:
                self.peeked.append(next(self.iterator))
            except StopIteration:
                return


class Runner:
    def __init__(
        self,
        dry_run: bool = False,
        pretty_print: bool = True,
        env: Optional[Dict[str, str]] = None,
    ):
        self.dry_run = dry_run
        self.pretty_print = pretty_print
        self.env = env

    def __call__(self, *args, env: Optional[Dict[str, str]] = None):
        if self.dry_run:
            print(self._format_cmd(*args, env=env))
            return

        self_env = None
        if self.env is None:
            self_env = {}

        if env is None:
            env = {}

        # Includes `os.environ`, since `subprocess.check_call` sets
        # the entire environment, and parent environment must be
        # explicitly forwarded.
        env = {**os.environ, **self_env, **env}
        subprocess.check_call(cmd, env=env)

    def _format_cmd(self, *args, env: Optional[Dict[str, str]] = None):
        self_env = None
        if self.env is None:
            self_env = {}

        if env is None:
            env = {}

        # Excludes `os.environ`, since any copy/paste use of the
        # printed command would implicitly inherit the parent
        # environment.
        env = {**self_env, **env}

        word_sep = " "
        line_sep = " \\\n    " if self.pretty_print else word_sep

        parts = []

        for key, value in env.items():
            parts.append(f"{key}={value}")
            parts.append(line_sep)

        iter_args = PeekIterator(args)
        while arg := next(iter_args, None):
            # Long flags get placed on their own line.
            is_long_flag = arg.startswith("--")

            # Short flags get placed inline if they have no arguments,
            # but get placed on their own line if they have an
            # argument.
            is_short_flag_with_arg = (
                arg.startswith("-")
                and iter_args.has_next()
                and not iter_args.peek().startswith("-")
            )
            if is_long_flag or is_short_flag_with_arg:
                if parts:
                    parts[-1] = line_sep
                opts = []
                while iter_args.has_next() and not iter_args.peek().startswith("-"):
                    opts.append(next(iter_args))

                # With 1 or 2 arguments, place on the same line as the
                # flag itself.  For 3 or more arguments, place each
                # argument on a separate line.
                opt_sep = line_sep if len(opts) >= 3 else word_sep

                parts.append(arg)
                parts.append(opt_sep)
                for opt in opts:
                    parts.append(opt)
                    parts.append(opt_sep)
                parts[-1] = line_sep

            else:
                # Position argument, separate by word
                parts.append(arg)
                parts.append(word_sep)

        # Easier to remove the last `word_sep` or `line_sep` than to
        # make each `parts.append` be conditional on there being
        # subsequent text.
        parts.pop()

        return "".join(parts)


if "PYTEST_VERSION" in os.environ:
    import textwrap

    import pytest

    def test_basic():
        runner = Runner()
        cmd = runner._format_cmd("basic_command", "arg")
        assert cmd == "basic_command arg"

    def test_env_basic():
        runner = Runner(pretty_print=False)
        cmd = runner._format_cmd("command", env={"ENVVAR": "env_var_value"})
        assert cmd == "ENVVAR=env_var_value command"

    def test_env_pretty_print():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd("command", env={"ENVVAR": "env_var_value"})
        expected = textwrap.dedent(r"""
            ENVVAR=env_var_value \
                command
        """).strip()
        assert cmd == expected

    def test_pretty_print_short_flag():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd("command", "-s")
        expected = textwrap.dedent(r"""
            command -s
        """).strip()
        assert cmd == expected

    def test_pretty_print_short_option():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd("command", "-i", "arg1", "-o", "arg2")
        expected = textwrap.dedent(r"""
            command \
                -i arg1 \
                -o arg2
        """).strip()
        assert cmd == expected

    def test_pretty_print_long_option():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd("command", "--input", "arg1", "--output", "arg2")
        expected = textwrap.dedent(r"""
            command \
                --input arg1 \
                --output arg2
        """).strip()
        assert cmd == expected

    def test_pretty_print_short_option_with_short_flags():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd("command", "-i", "arg1", "-s", "-t")
        expected = textwrap.dedent(r"""
            command \
                -i arg1 \
                -s -t
        """).strip()
        assert cmd == expected

    def test_pretty_print_short_option_with_long_flags():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd("command", "-i", "arg1", "--flag1", "--flag2")
        expected = textwrap.dedent(r"""
            command \
                -i arg1 \
                --flag1 \
                --flag2
        """).strip()
        assert cmd == expected

elif __name__ == "__main__":
    import sys

    import pytest

    pytest.main(sys.argv)
