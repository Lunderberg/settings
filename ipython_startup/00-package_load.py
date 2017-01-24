import inspect
import importlib

class ModuleLoader:
    def __init__(self, libname, import_as = None):
        self.libname = libname
        if import_as is None:
            self.import_as = libname
        else:
            self.import_as = import_as

    def __getattr__(self, name):
        module = importlib.import_module(self.libname)
        frame = inspect.stack()[1][0]
        frame.f_locals[self.import_as] = module
        return getattr(module, name)

np = ModuleLoader('numpy','np')
plt = ModuleLoader('matplotlib.pyplot','plt')

del ModuleLoader
