"""
Usage:

from lunderberg_tvm_instrument import PrintTransformSequence
with tvm.transform.PassContext(instruments=[PrintTransformSequence()]):
    lib = relay.vm.compile(mod, target="llvm -mcpu=cascadelake", params=params)

from lunderberg_tvm_instrument import PrintTransformSequence
with PrintTransformSequence.context():
    lib = relay.vm.compile(mod, target="llvm -mcpu=cascadelake", params=params)

import pytest
@pytest.fixture(autouse=True)
def very_verbose():
    from lunderberg_tvm_instrument import PrintTransformSequence
    context = PrintTransformSequence.context()
    with context:
        yield
"""

import contextlib

import black
import pygments
import pygments.formatters
import pygments.lexers.python

import tvm.relay
from tvm.ir.instrument import pass_instrument


@pass_instrument
class PrintTransformSequence:
    def __init__(
        self,
        transforms=None,
        print_before_after=True,
        print_style="tvmscript",
        pygments_style="dracula",
        max_blacken_length=64 * 1024,
        max_pygments_length=16 * 1024,
        ignore_passes_inside=None,
    ):
        """Construct the Instrumenter

        Parameters
        ----------
        transforms : Optional[Union[str, List[str]]]

            Which transforms should have their name printed when they
            are being applied.  If None, then all transforms are
            printed.  If a list of strings, only those passes are
            printed.

        print_before_after : Union[bool, List[str]]

            Which transforms should have their before/after TIR
            printed.  If True, all passes are printed.  If False, no
            passes are printed.  If a list of strings, only those
            passes have before/after printed.

            Only applies to transforms that are printed based on the
            `transforms` argument.

        print_style: str

            If "tvmscript", print a module as TVMScript.  If "tir",
            print a module using str().  If "function_names", only
            print the function names.

        pygments_style: Optional[str]

            The pygments style for highlighting.  If `None`, no
            formatting is applied.  Defaults to "dracula".

        max_blacken_length: Optional[int]

            The maximum length of a module, in bytes, in order to
            apply `black.format_str` on it.  If `None`, no limit is
            applied.

        max_pygments_length: Optional[int]

            The maximum length of a module, in bytes, in order to
            apply `pygments.highligh` on it.  If `None`, no limit is
            applied.
        """
        if isinstance(transforms, str):
            self.transforms = [transforms]
        else:
            self.transforms = transforms

        self.nesting_level = 0
        self.current_nested_passes = []
        self.print_before_after = print_before_after
        self.div_length = 40
        self.print_style = print_style
        self.pygments_style = pygments_style

        self.max_blacken_length = max_blacken_length
        self.max_pygments_length = max_pygments_length
        self.ignore_passes_inside = ignore_passes_inside

    @classmethod
    def context(cls, *args, **kwargs):
        obj = cls(*args, **kwargs)
        return tvm.transform.PassContext(instruments=[obj])

    def _print_before_after(self, name):
        if isinstance(self.print_before_after, bool):
            return self.print_before_after
        else:
            return name in self.print_before_after

    def _indent(self):
        return " " * (4 * self.nesting_level)

    def run_before_pass(self, mod, info):
        self.current_nested_passes.append(info.name)
        if self.transforms is None or info.name in self.transforms:
            print_before_after = self._print_before_after(info.name)
            if print_before_after:
                self.print_header(f"Before {info.name}")
                self.print_mod(mod, name=f"ModBefore{info.name}")
                self.print_footer()
            else:
                self.print_header(f"{info.name}")

            self.nesting_level += 1

    def run_after_pass(self, mod, info):
        self.current_nested_passes.pop()
        if self.transforms is None or info.name in self.transforms:
            self.nesting_level -= 1

            print_before_after = self._print_before_after(info.name)
            if print_before_after:
                self.print_header(f"After {info.name}")
                self.print_mod(mod, name=f"ModAfter{info.name}")
                self.print_footer()

    def print_header(self, header):
        div_around_header = self.div_length - len(header) - 2
        left_div_length = div_around_header // 2
        right_div_length = div_around_header - left_div_length
        header = "".join(
            [
                "-" * left_div_length,
                " ",
                header,
                " ",
                "-" * right_div_length,
            ]
        )
        print(self._indent() + header, flush=True)

    def print_footer(self):
        footer = "-" * self.div_length
        print(self._indent() + footer, flush=True)

    def as_tvmscript(self, mod, name=None):
        text = mod.script(syntax_sugar=True, show_meta=False, name=name)

        if self.max_blacken_length is None or len(text) < self.max_blacken_length:
            with contextlib.suppress(black.InvalidInput):
                text = black.format_str(text, mode=black.FileMode())

        if self.pygments_style is not None:
            if self.max_pygments_length is None or len(text) < self.max_pygments_length:
                text = pygments.highlight(
                    text,
                    pygments.lexers.python.Python3Lexer(),
                    pygments.formatters.Terminal256Formatter(style=self.pygments_style),
                )
        return text

    def print_mod(self, mod, name=None):
        def print_tir():
            text = []
            for name, func in sorted(
                mod.functions.items(), key=lambda kv: kv[0].name_hint
            ):
                text.append(f"{name} = {func}")
            return "\n".join(text)

        if self.print_style == "tvmscript":
            text = self.as_tvmscript(mod, name)

        elif self.print_style == "tir":
            text = print_tir()

        elif self.print_style == "function_names":
            text = "\n".join(var.name_hint for var in mod.functions)

        else:
            raise RuntimeError(f"Unknown print style {self.print_style}")

        indent = self._indent()
        text = "\n".join(indent + line for line in text.split("\n"))
        print(text, flush=True)


@pass_instrument
class VerifyWellFormed:
    def run_before_pass(self, mod, info):
        if not tvm.tir.analysis.verify_well_formed(mod, assert_mode=False):
            print("-*" * 30 + "-")
            print(f"Failure prior to running {info.name}")
            print(mod)
            print("-*" * 30 + "-", flush=True)
            tvm.tir.analysis.verify_well_formed(mod)

    def run_after_pass(self, mod, info):
        if not tvm.tir.analysis.verify_well_formed(mod, assert_mode=False):
            print("-*" * 30 + "-")
            print(f"Failure after running {info.name}")
            print(mod)
            print("-*" * 30 + "-", flush=True)
            tvm.tir.analysis.verify_well_formed(mod)
