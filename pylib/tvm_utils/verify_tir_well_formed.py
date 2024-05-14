"""
Usage:

from tvm_utils import VerifyWellFormed
with tvm.transform.PassContext(instruments=[VerifyWellFormed()]):
    lib = relay.vm.compile(mod, target="llvm -mcpu=cascadelake", params=params)

"""

import tvm
from tvm.ir.instrument import pass_instrument


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
