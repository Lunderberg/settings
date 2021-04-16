class ModuleLoader:
    def __init__(self, libname, import_as=None):
        self.libname = libname
        if import_as is None:
            self.import_as = libname
        else:
            self.import_as = import_as

    def __getattr__(self, name):
        import inspect, importlib

        module = importlib.import_module(self.libname)
        frame = inspect.stack()[1][0]
        frame.f_locals[self.import_as] = module
        return getattr(module, name)


# General data analysis
np = ModuleLoader("numpy", "np")
pd = ModuleLoader("pandas", "pd")
plt = ModuleLoader("matplotlib.pyplot", "plt")

# tvm import
tvm = ModuleLoader("tvm", "tvm")
te = ModuleLoader("tvm.te", "te")

del ModuleLoader
