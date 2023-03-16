from __future__ import annotations

import importlib.util
import inspect
import functools
import pathlib

from types import ModuleType

_typing = False
if _typing:
    from typing import Callable
    from typing import Union
del _typing


def import_module_from_path(module_name: str, package_path: str) -> Union[None, ModuleType]:
    module_name = module_name.split(".")[0]
    spec = importlib.util.spec_from_file_location(module_name, package_path)
    if not spec:
        print("No spec found!")
        return

    module: ModuleType = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert loader, f"No loader found for {package_path} - {module_name}"
    loader.exec_module(module)
    return module


from . import api

val1 = api.checkout("")
val1 = api.checkout([""])


def get_source_code(file: pathlib.Path) -> str:
    module = import_module_from_path(file.stem, str(file))
    assert module
    for attr_name in dir(module):
        attribute = getattr(module, attr_name)
        # if isinstance(attribute, types.FunctionType):
        # 	signature = inspect.signature(attribute)
        # 	argspec = inspect.getfullargspec(attribute)
        # 	source_lines = inspect.getsourcelines(attribute)
        # 	# print(argspec.args)
        # 	# print(signature)
        # 	# print(argspec.annotations)
        # 	# print(source_lines)
        # 	# print("----")

        # print(attribute)
        if inspect.isclass(attribute):
            for attr_name in dir(attribute):
                class_attribute = getattr(attribute, attr_name)
                if inspect.isfunction(class_attribute) or isinstance(class_attribute, functools._lru_cache_wrapper):
                    signature = inspect.signature(class_attribute)
                    parameters = signature.parameters.values()
                    args = []
                    kwargs: list[inspect.Parameter] = []
                    for arg in parameters:
                        if arg.default == inspect._empty:
                            args.append(arg)
                            continue

                        kwargs.append(arg)

                    args_str = ", ".join((arg.name for arg in args))

                    def _empty_string():
                        return '""'

                    kwargs_str = "".join(
                        f", {kwarg.name}={_empty_string() if isinstance(kwarg.default, str) else kwarg.default}"
                        for kwarg in kwargs
                    )
                    function_header = f"def {attr_name}({args_str}{kwargs_str}):"
                    parameters_wihout_self = [arg for arg in parameters if arg.name != "self"]
                    annotations = [arg.annotation if arg.annotation != inspect._empty else "Any" for arg in parameters_wihout_self]
                    return_type = signature.return_annotation
                    return_type_str = "Any" if return_type == inspect._empty else return_type
                    type_annotation = f"\t# type: ({', '.join(annotations)}) -> {return_type_str}"
                    print(function_header)
                    print(type_annotation)
                    print("----")
            print("----")


if __name__ == "__main__":
    get_source_code(
        pathlib.Path(
            r"C:\p4ws\sharkmob\Tools\OpenPype\OpenPype-3-14-2\openpype\modules\version_control\backends\perforce\api.py"
        )
    )
