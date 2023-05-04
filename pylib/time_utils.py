#!/usr/bin/env python3

import datetime
import re
import sys
import termios
import time


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
    if not sys.stdin.isatty():
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
            if chars[-1] == 'R':
                break
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, old_attrs)

    string = ''.join(chars)

    if match := re.match(r".*\[(?P<y>\d*);(?P<x>\d*)R", string):
        return (int(match.group("x"))-1, int(match.group("y"))-1)
    else:
        return None


def advance_line():
    pos = get_cursor_pos()
    if pos and pos[0]:
        print('')

def get_clear_length(message_length):
    if pos := get_cursor_pos():
        return pos[0] + 1
    else:
        return message_length+40

class Timer:
    def __init__(self, message=None):
        self.message = message

        self.start_datetime = None
        self.end_datetime = None
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_datetime = datetime.datetime.now()
        self.start_time = time.perf_counter()

        if self.message is not None:
            advance_line()
            print("[{}]\t{}".format(self.start_datetime, self.message), end="", flush=True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_datetime = datetime.datetime.now()
        self.end_time = time.perf_counter()

        self.elapsed_time = datetime.timedelta(seconds=self.end_time - self.start_time)

        if self.message is not None:
            clear_len = get_clear_length(len(self.message))
            print(
                "\r{}\r[{}]\t{}".format(
                    " " * clear_len, format_timedelta(self.elapsed_time), self.message
                ),
                flush=True
            )
