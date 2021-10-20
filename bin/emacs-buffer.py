#!/usr/bin/env python3

import argparse
import datetime
import inspect
import select
import subprocess
import sys


class EmacsRedirect:
    def __init__(
        self,
        buffer_name,
        append=False,
        tee=False,
        raw=False,
        verbose=False,
        max_chars_per_write=500,
        min_time_between_write=datetime.timedelta(seconds=0.5),
    ):
        self.buffer_name = buffer_name
        self.max_chars_per_write = max_chars_per_write
        self.min_time_between_write = min_time_between_write
        self.verbose = verbose
        self.tee = tee
        self.raw = raw

        self.chars = []
        self.last_write_time = datetime.datetime.now()

        if not append:
            self.send_command(self.command_clear_buffer())

        self.send_command(self.command_config_buffer())

    def time_since_write(self):
        return datetime.datetime.now() - self.last_write_time

    def read_from(self, f):
        eof = False

        while not eof:
            read_list, _, _ = select.select([f], [], [], 0.1)

            if read_list:
                char = f.read(1)
                if char:
                    self.chars.append(char)
                else:
                    eof = True

            flush_full_buffer = len(self.chars) >= self.max_chars_per_write
            flush_partial_buffer = self.chars and (
                self.time_since_write() > self.min_time_between_write
            )
            flush_eof = self.chars and eof

            if flush_full_buffer or flush_partial_buffer or flush_eof:
                self.flush_buffer()

    def flush_buffer(self):
        if self.tee:
            print("".join(self.chars), end="")

        self.send_command(self.command_append_text())
        self.chars = []
        self.last_write_time = datetime.datetime.now()

    def send_command(self, command):
        if self.verbose:
            print(inspect.cleandoc(command))
        return subprocess.check_output(["emacsclient", "--eval", command])

    def command_config_buffer(self):
        commands = []

        # Store the location of the pipe's pseudo cursor in a local
        # variable, in case the user moves the mark around while text
        # is being written.
        commands.append(
            """
            (unless (boundp 'pipe-cursor-loc)
                (setq-local pipe-cursor-loc (point-max)))
            """
        )

        # Disable modes that change the behavior of (newline)
        commands.extend(
            [
                "(electric-indent-local-mode 0)",
                "(auto-fill-mode 0)",
            ]
        )

        buf = self.command_get_buffer()
        commands = "\n".join(commands)
        command = f"""
        (with-current-buffer {buf}
          {commands}
        )
        """
        return command

    def command_get_buffer(self):
        return f'(get-buffer-create "{self.buffer_name}")'

    def command_clear_buffer(self):
        buf = self.command_get_buffer()
        return f"""
        (with-current-buffer {buf} (erase-buffer))
        """

    def command_append_text(self):
        escape = {
            '"': '\\"',
            "\\": "\\\\",
        }

        commands = []
        current_string = []

        def finish_current_string():
            nonlocal commands
            nonlocal current_string
            if current_string:
                string = "".join(current_string)
                # Overwrite-mode only applies to self-insert-command,
                # not to insert.  Therefore, we need to explicitly
                # overwrite any text.
                commands.append(
                    f"(delete-char (max 0 (min {len(string)} (- (line-end-position) (point)))))"
                )
                commands.append(f'(insert "{string}")')
                current_string = []

        for c in self.chars:
            if self.raw:
                current_string.append(escape.get(c, c))
            elif c == "\r":
                finish_current_string()
                commands.append("(move-beginning-of-line 1)")
            elif c == "\n":
                finish_current_string()
                command = """
                (move-end-of-line 1)
                (if (= (point) (point-max))
                  (newline)
                 (forward-char)
                )
                """
                commands.append(command)
            else:
                current_string.append(escape.get(c, c))
        finish_current_string()

        buf = self.command_get_buffer()
        commands = "\n".join(commands)

        command = f"""
        (with-current-buffer {buf}
          (let* ((is-at-end (= (point) (point-max)))
                 (windows (get-buffer-window-list))
                 (windows-at-end (seq-filter (lambda (window) (= (window-point window) (point-max)))
                                             windows))
                 )
            (save-mark-and-excursion
              (goto-char pipe-cursor-loc)
              {commands}
              (when (fboundp 'ansi-color-apply-on-region)
                (ansi-color-apply-on-region pipe-cursor-loc (point)))
              (setq-local pipe-cursor-loc (point))
              )
            (when is-at-end
              (goto-char (point-max)))
            (dolist (window windows-at-end)
              (set-window-point window (point-max)))
            )
          )
        """
        return command


def main(args):
    redirect = EmacsRedirect(
        buffer_name=args.buffer_name,
        append=args.append,
        tee=args.tee,
        verbose=args.verbose,
    )
    redirect.read_from(sys.stdin)


def arg_main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a",
        "--append",
        action="store_true",
        help="Append to the emacs buffer instead of overwriting.",
    )
    parser.add_argument(
        "-b",
        "--buffer",
        default="*pipe-command*",
        dest="buffer_name",
        help="The emacs buffer in which the output should be sent.",
    )
    parser.add_argument(
        "-t",
        "--tee",
        action="store_true",
        help="Print to stdout in addition to sending to the output buffer.",
    )
    parser.add_argument(
        "-r",
        "--raw",
        action="store_true",
        help=r"Send control characters such as \r to the emacs buffer unmodified.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print all commands that are sent to the emacsclient",
    )

    args = parser.parse_args()
    main(args)


if __name__ == "__main__":
    arg_main()
