#!/usr/bin/env python3

import argparse
import contextlib
import datetime
import itertools
import queue
import re
import signal
import subprocess
import threading
import time


import uniplot


class TerminalCommands:
    ESCAPE = "\033"

    SAVE_CURSOR_POSITION = ESCAPE + "7"
    SWITCH_TO_ALTERNATE_SCREEN = ESCAPE + "[?47h"

    CLEAR_SCREEN = ESCAPE + "[2J"
    RESTORE_NORMAL_SCREEN = ESCAPE + "[?47l"
    RESTORE_CURSOR_POSITION = ESCAPE + "8"

    @classmethod
    def save_cursor_position(cls):
        print(cls.SAVE_CURSOR_POSITION, end="")

    @classmethod
    def switch_to_alternate_screen(cls):
        print(cls.SWITCH_TO_ALTERNATE_SCREEN, end="")

    @classmethod
    def clear_screen(cls):
        print(cls.CLEAR_SCREEN, end="")

    @classmethod
    def restore_normal_screen(cls):
        print(cls.RESTORE_NORMAL_SCREEN, end="")

    @classmethod
    def restore_cursor_position(cls):
        print(cls.RESTORE_CURSOR_POSITION, end="")

    @classmethod
    def use_alternate_screen(cls):
        class AlternateScreen:
            def __enter__(self):
                cls.save_cursor_position()
                cls.switch_to_alternate_screen()
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                cls.clear_screen()
                cls.restore_normal_screen()
                cls.restore_cursor_position()

        return AlternateScreen()


def get_ssh_name(ssh_name):
    output = subprocess.check_output(["ssh", "-G", ssh_name], encoding="utf-8")
    for line in output.split("\n"):
        if not line.strip():
            continue

        key, value = line.split(maxsplit=1)

        if key == "hostname":
            return value

    return None


def is_valid_server(server):
    try:
        subprocess.check_output(["nslookup", server], encoding="utf-8")
        return True
    except subprocess.CalledProcessError:
        return None


class ServerPing:
    def __init__(self, server, max_data_length=datetime.timedelta(minutes=5)):
        self.server = server
        self.ping_target = self.get_ping_target(server)

        self.max_data_length = max_data_length
        self.running = False
        self.data = []

    @staticmethod
    def get_ping_target(server):
        if is_valid_server(server):
            return server

        ssh_name = get_ssh_name(server)
        if ssh_name is not None and is_valid_server(ssh_name):
            return ssh_name

        raise ValueError(f"Can't ping {server}")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def start(self):
        if self.running:
            return

        self.running = True

        self._thread = threading.Thread(target=self.worker_thread, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def worker_thread(self):
        regex = "".join(
            [
                r"\[",
                r"(?P<timestamp>\d+(\.\d+)?)",
                r"\].*time=",
                r"(?P<rtt>\d+(\.\d+)?)",
                r" ms",
            ]
        )
        with contextlib.ExitStack() as stack:
            proc = subprocess.Popen(
                ["ping", self.ping_target, "-D"],
                stdout=subprocess.PIPE,
                encoding="utf-8",
            )
            stack.callback(proc.kill)

            while self.running and proc.poll() is None:
                line = proc.stdout.readline()
                res = re.match(regex, line)

                if res is None:
                    continue

                timestamp = datetime.datetime.fromtimestamp(
                    float(res.group("timestamp"))
                )
                rtt = float(res.group("rtt"))

                self._append_data(timestamp, rtt)

            self.running = False

    def _append_data(self, timestamp, rtt):
        cutoff = datetime.datetime.now() - self.max_data_length
        self.data = [
            (ts, rtt)
            for ts, rtt in itertools.chain(self.data, [(timestamp, rtt)])
            if ts > cutoff
        ]


class PingPlotter:
    def __init__(
        self,
        servers,
        max_data_length=datetime.timedelta(minutes=5),
        redraw_period=datetime.timedelta(seconds=5),
    ):
        self.pingers = [
            ServerPing(server, max_data_length=max_data_length) for server in servers
        ]
        self.collecting = False
        self.plotting = False
        self.redraw_period = redraw_period

        self._command_queue = queue.Queue()

    def __enter__(self):
        self.start_collecting()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop_collecting()
        self.stop_plotting()

    def start_collecting(self):
        for pinger in self.pingers:
            pinger.start()
        self.collecting = True

    def stop_collecting(self):
        for pinger in self.pingers:
            pinger.stop()
        self.collecting = False

    def start_plotting(self):
        if self.plotting:
            return

        self.plotting = True
        self._plot_thread = threading.Thread(target=self.plot_thread, daemon=True)
        self._plot_thread.start()

    def stop_plotting(self):
        if not self.plotting:
            return

        self.plotting = False
        self._command_queue.put("stop")
        self._plot_thread.join()
        self._plot_thread = None

    def plot_thread(self):
        with TerminalCommands.use_alternate_screen():

            next_draw = datetime.datetime.now() + self.redraw_period

            while self.plotting:
                until_next_draw = (next_draw - datetime.datetime.now()).total_seconds()

                try:
                    command = self._command_queue.get(timeout=until_next_draw)
                except queue.Empty:
                    command = None

                if command == "stop":
                    break
                elif command is None:
                    TerminalCommands.clear_screen()
                    self.plot()
                    next_draw = datetime.datetime.now() + self.redraw_period

    def plot(self):
        now = datetime.datetime.now()
        plot_data = {
            pinger.server: [
                ((ts - now).total_seconds(), rtt) for ts, rtt in pinger.data
            ]
            for pinger in self.pingers
        }

        if len(self.pingers) == 1:
            server = self.pingers[0].server
            title = f"Ping Time, {server}"
            legend_labels = None
        else:
            title = "Ping Time"
            legend_labels = [server for server, data in plot_data.items()]

        xdata = [[ts for ts, rtt in data] for data in plot_data.values()]
        ydata = [[rtt for ts, rtt in data] for data in plot_data.values()]

        uniplot.plot(
            xs=xdata,
            ys=ydata,
            x_max=0,
            x_unit="s",
            y_unit="ms",
            title=title,
            legend_labels=legend_labels,
            color=True,
        )


def main(args):
    with contextlib.ExitStack() as stack:
        ping_plotter = stack.enter_context(PingPlotter(args.servers))

        ping_plotter.start_collecting()
        ping_plotter.start_plotting()

        try:
            signal.pause()
        except KeyboardInterrupt:
            pass


def arg_main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pdb",
        action="store_true",
        help="Start a pdb post mortem on uncaught exception",
    )
    parser.add_argument(
        "-s",
        "--servers",
        nargs="+",
        required=True,
        help="The server(s) to ping.",
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
