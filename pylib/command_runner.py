#!/usr/bin/env python3

import collections
import functools
import os
import pathlib
import subprocess
import sys

from typing import Dict, List, Optional, Tuple, Iterable, Union


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

    def _normalize(
        self,
        cmd: List[str],
        env: Optional[Dict[str, str]] = None,
    ) -> Tuple[List[str], Dict[str, str]]:
        self_env = self.env
        if self_env is None:
            self_env = {}

        if env is None:
            env = {}

        env = {**self_env, **env}
        return cmd, env

    def __call__(self, cmd: List[str], env: Optional[Dict[str, str]] = None):
        if self.dry_run:
            print(self._format_cmd(cmd, env=env))
            return

        cmd, env = self._normalize(cmd, env)

        # Includes `os.environ`, since `subprocess.check_call` sets
        # the entire environment, and parent environment must be
        # explicitly forwarded.
        env = {**os.environ, **self_env, **env}
        subprocess.check_call(cmd, env=env)

    def _format_cmd(self, cmd, env: Optional[Dict[str, str]] = None):
        # Excludes `os.environ` fom `env`, since any copy/paste use of
        # the printed command would implicitly inherit the parent
        # environment.
        cmd, env = self._normalize(cmd, env)

        word_sep = " "
        line_sep = " \\\n    " if self.pretty_print else word_sep

        parts = []

        for key, value in env.items():
            parts.append(f"{key}={value}")
            parts.append(line_sep)

        arg_is_executable = True
        iter_args = PeekIterator(cmd)
        while arg := next(iter_args, None):
            is_long_flag = arg.startswith("--")
            is_short_flag_with_arg = (
                arg.startswith("-")
                and iter_args.has_next()
                and not iter_args.peek().startswith("-")
            )

            # fmt: off
            is_start_of_group = any((
                # The executable owns any positional arguments that
                # follow, and those positional arguments may be placed on
                # the same line.
                arg_is_executable,

                # Long flags get placed on their own line.
                is_long_flag,

                # Short flags get placed inline if they have no arguments,
                # but get placed on their own line if they have an
                # argument.
                is_short_flag_with_arg,
            ))
            # fmt: on

            if is_start_of_group:
                if parts:
                    parts[-1] = line_sep

                opts = []
                if "=" not in arg and arg != "--":
                    while iter_args.has_next() and not iter_args.peek().startswith("-"):
                        opts.append(next(iter_args))

                # With 1 or 2 arguments, place on the same line as the
                # flag itself.  For 3 or more arguments, place each
                # argument on a separate line.
                opt_sep = line_sep if len(opts) >= 3 else word_sep

                # A command with no positional arguments doesn't need
                # a line separation afterwards.  (Though this may be
                # replaced with a line separation anyways based on the
                # following argument.)
                end_sep = opt_sep if arg_is_executable else line_sep

                parts.append(arg)
                parts.append(opt_sep)
                for opt in opts:
                    parts.append(opt)
                    parts.append(opt_sep)
                parts[-1] = end_sep

            else:
                # Position argument, separate by word
                parts.append(arg)
                parts.append(word_sep)

            # After processing the first argument, following arguments
            # do not specify the name of a command.  The exception is
            # when the argument is `--`, which is often used to treat
            # all following argments as positional, and makes it
            # easier to define arguments that will be provided to a
            # subcommand.
            arg_is_executable = arg == "--"

        # Easier to remove the last `word_sep` or `line_sep` than to
        # make each `parts.append` be conditional on there being
        # subsequent text.
        parts.pop()

        return "".join(parts)


class DockerMount:
    def __init__(
        self,
        src: Union[str, pathlib.Path],
        dst: Optional[Union[str, pathlib.Path]] = None,
    ):
        self.src = pathlib.Path(src).resolve()

        if dst is None:
            dst = src
        self.dst = pathlib.Path(dst).resolve()


class DockerRunner(Runner):
    def __init__(
        self,
        docker_image: str,
        mounts: Optional[
            Union[str, pathlib.Path, Iterable[Union[str, pathlib.Path]]]
        ] = None,
        as_root: bool = False,
        *args,
        **kwargs,
    ):
        self.docker_image = docker_image
        self.mounts = self._normalize_mounts(mounts)
        self.as_root = as_root
        super().__init__(*args, **kwargs)

    @staticmethod
    def _normalize_mounts(
        arg_mounts: Optional[
            Union[str, pathlib.Path, Iterable[Union[str, pathlib.Path]]]
        ],
    ) -> List[DockerMount]:
        mounts = []
        if arg_mounts is not None:
            if isinstance(arg_mounts, Iterable) and not isinstance(arg_mounts, str):
                iter_arg_mounts = iter(arg_mounts)
            else:
                iter_arg_mounts = iter((arg_mounts,))

            for arg in iter_arg_mounts:
                if not isinstance(arg, DockerMount):
                    arg = DockerMount(arg)
                mounts.append(arg)

        return mounts

    @staticmethod
    @functools.cache
    def _docker_is_rootful() -> Optional[bool]:
        """Check if the docker installation defaults to root

        Returns
        -------
        is_rootful: Optional[bool]

            True if the docker installation defaults to root.  False
            for sane docker installations (i.e. non-default "rootless"
            installs, or "podmand" aliased to docker) that do not
            default to root.

            If no docker installation is located, returns `None`.

        """
        try:
            output = subprocess.check_output(
                ["docker", "info", "-f", "{{ .Host.Security.Rootless }}"],
                encoding="utf-8",
            )
        except FileNotFoundError:
            return None

        return output.strip() != "true"

    def _normalize(
        self,
        cmd: List[str],
        env: Optional[Dict[str, str]] = None,
    ) -> Tuple[List[str], Dict[str, str]]:
        orig_cmd, env = super()._normalize(cmd, env)

        io_flags = []
        if sys.stdin.isatty():
            io_flags.append("--interactive")
        if sys.stdout.isatty():
            io_flags.append("--tty")

        env_flags = [f"--env={key}={value}" for key, value in env.items()]

        mount_flags = [
            f"--mount=type=bind,src={mnt.src},dst={mnt.dst}" for mnt in self.mounts
        ]

        abdicate_root_flags = []
        if self._docker_is_rootful() in (None, True) and not self.as_root:
            uid = os.getuid()
            gid = os.getgid()
            abdicate_root_flags.append(f"--user={uid}:{gid}")

        cmd = [
            "docker",
            "run",
            "--rm",
            *io_flags,
            *env_flags,
            *mount_flags,
            *abdicate_root_flags,
            self.docker_image,
            *orig_cmd,
        ]
        return cmd, {}


if "PYTEST_VERSION" in os.environ:
    import textwrap
    import types

    import pytest

    def test_basic():
        runner = Runner()
        cmd = runner._format_cmd(["basic_command", "arg"])
        assert cmd == "basic_command arg"

    def test_env_in_command():
        runner = Runner(pretty_print=False)
        cmd = runner._format_cmd(["command"], env={"ENVVAR": "env_var_value"})
        assert cmd == "ENVVAR=env_var_value command"

    def test_env_in_runner():
        runner = Runner(pretty_print=False, env={"ENVVAR": "env_var_value"})
        cmd = runner._format_cmd(["command"])
        assert cmd == "ENVVAR=env_var_value command"

    def test_env_in_command_overrides_runner():
        runner = Runner(pretty_print=False, env={"ENVVAR": "runner_value"})
        cmd = runner._format_cmd(["command"], env={"ENVVAR": "cmd_value"})
        assert cmd == "ENVVAR=cmd_value command"

    def test_env_pretty_print():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd(["command"], env={"ENVVAR": "env_var_value"})
        expected = textwrap.dedent(r"""
            ENVVAR=env_var_value \
                command
        """).strip()
        assert cmd == expected

    def test_pretty_print_short_flag():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd(["command", "-s"])
        expected = textwrap.dedent(r"""
            command -s
        """).strip()
        assert cmd == expected

    def test_pretty_print_short_option():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd(["command", "-i", "arg1", "-o", "arg2"])
        expected = textwrap.dedent(r"""
            command \
                -i arg1 \
                -o arg2
        """).strip()
        assert cmd == expected

    def test_pretty_print_long_option():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd(["command", "--input", "arg1", "--output", "arg2"])
        expected = textwrap.dedent(r"""
            command \
                --input arg1 \
                --output arg2
        """).strip()
        assert cmd == expected

    def test_pretty_print_short_option_with_short_flags():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd(["command", "-i", "arg1", "-s", "-t"])
        expected = textwrap.dedent(r"""
            command \
                -i arg1 \
                -s -t
        """).strip()
        assert cmd == expected

    def test_pretty_print_short_option_with_long_flags():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd(["command", "-i", "arg1", "--flag1", "--flag2"])
        expected = textwrap.dedent(r"""
            command \
                -i arg1 \
                --flag1 \
                --flag2
        """).strip()
        assert cmd == expected

    def test_pretty_print_few_positionals():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd(["command", "arg1", "arg2"])
        expected = "command arg1 arg2"
        assert cmd == expected

    def test_pretty_print_many_positionals():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd(["command", "arg1", "arg2", "arg3", "arg4"])
        expected = textwrap.dedent(r"""
            command \
                arg1 \
                arg2 \
                arg3 \
                arg4
        """).strip()
        assert cmd == expected

    def test_pretty_print_positional_after_flag():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd(
            ["command", "--flag=value", "arg1", "arg2", "arg3", "arg4"]
        )
        expected = textwrap.dedent(r"""
            command \
                --flag=value \
                arg1 arg2 arg3 arg4
        """).strip()
        assert cmd == expected

    def test_pretty_print_positional_after_flag():
        runner = Runner(pretty_print=True)
        cmd = runner._format_cmd(
            ["command", "--flag", "arg1", "--", "subcmd", "arg3", "arg4"]
        )
        expected = textwrap.dedent(r"""
            command \
                --flag arg1 \
                -- \
                subcmd arg3 arg4
        """).strip()
        assert cmd == expected

    @pytest.fixture
    def rootless_docker(monkeypatch):
        """Fixture to test as if the docker installation is rootless

        This simplfies test cases, since the `--user` flag is not
        produced, and doesn't need to be specified in the expected
        output for unrelated test cases.
        """
        monkeypatch.setattr(
            DockerRunner,
            "_docker_is_rootful",
            staticmethod(lambda: False),
        )

    @pytest.mark.parametrize("stdin", ["stdin", ""])
    @pytest.mark.parametrize("stdout", ["stdout", ""])
    def test_docker_run(monkeypatch, rootless_docker, stdin: str, stdout: str):
        monkeypatch.setattr(
            sys,
            "stdin",
            types.SimpleNamespace(isatty=lambda: bool(stdin)),
        )
        monkeypatch.setattr(
            sys,
            "stdout",
            types.SimpleNamespace(isatty=lambda: bool(stdout)),
        )

        runner = DockerRunner("image", pretty_print=False)
        cmd = runner._format_cmd(["command", "arg"])

        if stdin and stdout:
            expected = "docker run --rm --interactive --tty image command arg"
        elif stdin:
            expected = "docker run --rm --interactive image command arg"
        elif stdout:
            expected = "docker run --rm --tty image command arg"
        else:
            expected = "docker run --rm image command arg"
        assert cmd == expected

    @pytest.fixture
    def without_interactive_tty(monkeypatch):
        monkeypatch.setattr(
            sys,
            "stdin",
            types.SimpleNamespace(isatty=lambda: False),
        )
        monkeypatch.setattr(
            sys,
            "stdout",
            types.SimpleNamespace(isatty=lambda: False),
        )

    def test_docker_env(without_interactive_tty, rootless_docker):
        runner = DockerRunner("image", pretty_print=False)
        cmd = runner._format_cmd(
            ["command", "arg"],
            env={"ENVVAR": "value"},
        )

        expected = "docker run --rm --env=ENVVAR=value image command arg"
        assert cmd == expected

    @pytest.mark.parametrize("mount_type", [str, pathlib.Path, DockerMount])
    def test_docker_mount(without_interactive_tty, rootless_docker, mount_type):
        runner = DockerRunner(
            "image",
            pretty_print=False,
            mounts=mount_type("mnt_dir"),
        )
        cmd = runner._format_cmd(["command", "arg"])

        abs_mount = pathlib.Path.cwd().joinpath("mnt_dir")

        expected = (
            f"docker run --rm "
            f"--mount=type=bind,src={abs_mount},dst={abs_mount} "
            f"image command arg"
        )
        assert cmd == expected

    def test_docker_rootless(monkeypatch):
        monkeypatch.setattr(
            DockerRunner,
            "_docker_is_rootful",
            staticmethod(lambda: True),
        )

        runner = DockerRunner(
            "image",
            pretty_print=False,
            as_root=False,
        )
        cmd = runner._format_cmd(["command", "arg"])

        assert "--user" in cmd

    def test_docker_rootful(monkeypatch):
        """
        When running in an installation with rootful docker, if
        `as_root` is set, then the `--user` flag should not be
        present.
        """
        monkeypatch.setattr(
            DockerRunner,
            "_docker_is_rootful",
            staticmethod(lambda: True),
        )

        runner = DockerRunner(
            "image",
            pretty_print=False,
            as_root=True,
        )
        cmd = runner._format_cmd(["command", "arg"])

        assert "--user" not in cmd

elif __name__ == "__main__":
    import sys

    import pytest

    pytest.main(sys.argv)
