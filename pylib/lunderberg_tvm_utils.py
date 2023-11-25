import random

from tvm import relax


@relax.expr_functor.mutator
class UniqueNonsenseNames(relax.PyExprMutator):
    def __init__(self):
        super().__init__()

        def valid_names():
            for line in open("/etc/dictionaries-common/words"):
                line = line.strip()
                if line.islower() and line.isascii() and line.isalpha():
                    yield line

        self.names = list(valid_names())

        random.seed(0)
        self.names = random.sample(self.names, len(self.names))

    @classmethod
    def transform(cls):
        @ir.transform.module_pass(opt_level=0, name=cls.__name__)
        def fmutate(mod, context):
            new_module = {}
            mutator = cls()

            for gvar, func in mod.functions.items():
                if isinstance(func, relax.Function):
                    func = mutator.visit_expr(func)
                new_module[gvar] = func

            return tvm.IRModule(new_module)

        return fmutate

    def visit_var_def_(self, var):
        name = self.names.pop()
        if isinstance(var, relax.DataflowVar):
            new_var = relax.DataflowVar(name, var.struct_info)
        else:
            new_var = relax.Var(name, var.struct_info)
        return new_var
