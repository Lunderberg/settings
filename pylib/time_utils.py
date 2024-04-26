#!/usr/bin/env python3

import datetime
import functools
import re
import sys
import termios
import time
from typing import Optional

try:
    import nvtx
except ImportError:
    nvtx = None


def format_timedelta(d):
    rem = d.total_seconds()

    if rem > 86400:
        out_format = "{days:d}d{hours:02d}h{minutes:02d}m{seconds:02d}s"
    elif rem > 3600:
        out_format = "{hours:d}h{minutes:02d}m{seconds:02d}s"
    elif rem > 60:
        out_format = "{minutes:2d}m{seconds:02d}s"
    else:
        out_format = "{seconds:02d}.{ms:03d}s"

    days = int(rem // 86400)
    rem -= days * 86400

    hours = int(rem // 3600)
    rem -= hours * 3600

    minutes = int(rem // 60)
    rem -= minutes * 60

    seconds = int(rem)
    rem -= seconds

    ms = int(rem * 1000)
    rem -= ms / 1000

    return out_format.format(
        days=days, hours=hours, minutes=minutes, seconds=seconds, ms=ms
    )


# Adapted from https://stackoverflow.com/a/69582478/2689797
def get_cursor_pos():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return None

    old_attrs = termios.tcgetattr(sys.stdin)
    attrs = termios.tcgetattr(sys.stdin)
    attrs[3] = attrs[3] & ~(termios.ECHO | termios.ICANON)
    termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, attrs)

    try:
        chars = []
        sys.stdout.write("\x1b[6n")
        sys.stdout.flush()

        while True:
            chars.append(sys.stdin.read(1))
            if chars[-1] == "R":
                break
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, old_attrs)

    string = "".join(chars)

    if match := re.match(r".*\[(?P<y>\d*);(?P<x>\d*)R", string):
        return (int(match.group("x")) - 1, int(match.group("y")) - 1)
    else:
        return None


def advance_line():
    pos = get_cursor_pos()
    if pos and pos[0]:
        print("")


def get_clear_length(message_length):
    if pos := get_cursor_pos():
        return pos[0] + 1
    else:
        return message_length + 40


class Timer:
    def __init__(
        self,
        message: Optional[str] = None,
        print_to_stdout: bool = True,
        log_to_nvtx: bool = True,
    ):
        """Time a region of python

        Parameters
        ----------
        message: Optional[str]

            The message to be printed.  If no message is provided,
            then both `print_to_stdout` and `log_to_nvtx` have no
            effect.

        print_to_stdout: bool

            If true, print when entering/exiting the context.  If
            false, do not print to stdout.

        log_to_nvtx: bool

            If true, log when entering/exiting the context with NVTX.
            If false, do not log.

        """

        self.message = message
        self.print_to_stdout = print_to_stdout
        self.log_to_nvtx = log_to_nvtx

        self.start_datetime = None
        self.end_datetime = None
        self.start_time_ns = None
        self.end_time_ns = None

        self.is_running = False
        self._nvtx_context = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop(exc_type, exc_val, exc_tb)

    def __call__(self, func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return inner

    def start(self):
        if self.is_running:
            return
        self.is_running = True

        self.start_datetime = datetime.datetime.now()
        self.start_time_ns = time.perf_counter_ns()

        if self.message and self.print_to_stdout:
            advance_line()
            print(
                "[{}]\t{}".format(self.start_datetime, self.message), end="", flush=True
            )

        if self.message and self.log_to_nvtx and nvtx:
            self._nvtx_context = nvtx.annotate(self.message)
            self._nvtx_context.__enter__()

        self.is_running = False

    def stop(self, exc_type=None, exc_val=None, exc_tb=None):
        if not self.is_running:
            return
        self.is_running = False

        self.end_datetime = datetime.datetime.now()
        self.end_time_ns = time.perf_counter_ns()

        if self.message and self.print_to_stdout:
            clear_len = get_clear_length(len(self.message))
            print(
                "\r{}\r[{}]\t{}".format(
                    " " * clear_len, format_timedelta(self.elapsed), self.message
                ),
                flush=True,
            )

        if self._nvtx_context:
            nvtx_context = self._nvtx_context
            self._nvtx_context = None
            nvtx_context.__exit__(exc_type, exc_val, exc_tb)

    @property
    def elapsed(self) -> Optional[datetime.timedelta]:
        if self.start_time_ns is None or self.end_time_ns is None:
            return None
        else:
            return datetime.timedelta(
                microseconds=(self.end_time_ns - self.start_time_ns) / 1000
            )

    @property
    def elapsed_ns(self) -> Optional[int]:
        if self.start_time_ns is None or self.end_time_ns is None:
            return None
        else:
            return self.end_time_ns - self.start_time_ns
