import inspect

import tvm.relay
from tvm.ir.instrument import pass_instrument

# Usage:
#
# with tvm.transform.PassContext(instruments=PrintTransformSequence()):
#     lib = relay.vm.compile(mod, target="llvm -mcpu=cascadelake", params=params)
#
# with PrintTransformSequence.context():
#     lib = relay.vm.compile(mod, target="llvm -mcpu=cascadelake", params=params)
#
# @pytest.fixture(autouse=True)
# def very_verbose():
#     from lunderberg_tvm_instrument import PrintTransformSequence
#     context = PrintTransformSequence.context()
#     with context:
#         yield


@pass_instrument
class PrintTransformSequence:
    def __init__(self, transforms=None, print_tir=True):
        """Construct the Instrumenter

        Parameters
        ----------
        transforms : Optional[Union[str, List[str]]]

            Which transforms should have their name printed when they
            are being applied.  If None, then all transforms are
            printed.  If a list of strings, only those passes are
            printed.

        print_tir : Union[bool, List[str]]

            Which transforms should have their before/after TIR
            printed.  If True, all passes are printed.  If False, no
            passes are printed.  If a list of strings, only those
            passes have before/after printed.

            Only applies to transforms that are printed based on the
            `transforms` argument.

        """
        if isinstance(transforms, str):
            self.transforms = [transforms]
        else:
            self.transforms = transforms

        self.nesting_level = 0
        self.print_tir = print_tir
        self.div_length = 40

    @classmethod
    def context(cls, *args, **kwargs):
        obj = cls(*args, **kwargs)
        return tvm.transform.PassContext(instruments=[obj])

    def _print_tir(self, name):
        if isinstance(self.print_tir, bool):
            return self.print_tir
        else:
            return name in self.print_tir

    def _indent(self):
        return " " * (4 * self.nesting_level)

    def run_before_pass(self, mod, info):
        if self.transforms is None or info.name in self.transforms:
            print_tir = self._print_tir(info.name)
            if print_tir:
                self.print_header(f"Before {info.name}")
                self.print_mod(mod)
                self.print_footer()
            else:
                self.print_header(f"{info.name}")

            self.nesting_level += 1

    def run_after_pass(self, mod, info):
        if self.transforms is None or info.name in self.transforms:
            self.nesting_level -= 1

            print_tir = self._print_tir(info.name)
            if print_tir:
                self.print_header(f"After {info.name}")
                self.print_mod(mod)
                self.print_footer()

    def print_header(self, header):
        div_around_header = self.div_length - len(header) - 2
        left_div_length = div_around_header // 2
        right_div_length = div_around_header - left_div_length
        header = "".join(
            [
                "-" * left_div_length,
                header,
                "-" * right_div_length,
            ]
        )
        print(self._indent() + header)

    def print_footer(self):
        footer = "-" * self.div_length
        print(self._indent() + footer)

    def print_mod(self, mod):
        text = []
        for name, func in mod.functions.items():
            text.append(f"{name} = {func}")
        text = "\n".join(text)

        indent = self._indent()
        text = "\n".join(indent + line for line in text.split("\n"))
        print(text)
