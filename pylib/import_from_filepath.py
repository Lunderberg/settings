import importlib
import pathlib

from typing import Union, Optional


def import_from_filepath(
    filepath: Union[str, pathlib.Path], name: Optional[str] = None
):
    if isinstance(filepath, str):
        filepath = pathlib.Path(filepath)

    filepath = filepath.resolve()

    if name is None:
        name = "_".join(filepath.parts[1:])

    loader = importlib.machinery.SourceFileLoader(name, str(filepath))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    return mod
