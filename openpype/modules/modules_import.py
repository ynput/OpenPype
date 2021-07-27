import sys
import six


class __ModuleClass:
    __attributes__ = {}
    __defaults__ = set()

    def __getattr__(self, attr_name):
        return self.__attributes__.get(
            attr_name,
            type("Missing.{}".format(attr_name), (), {})
        )

    def __setattr__(self, attr_name, value):
        self.__attributes__[attr_name] = value

    def keys(self):
        return self.__attributes__.keys()

    def values(self):
        return self.__attributes__.values()

    def items(self):
        return self.__attributes__.items()


def _load_module_from_dirpath_py2(dirpath, module_name, dst_module_name):
    full_module_name = "{}.{}".format(dst_module_name, module_name)
    if full_module_name in sys.modules:
        return sys.modules[full_module_name]

    import imp

    dst_module = sys.modules[dst_module_name]

    fp, pathname, description = imp.find_module(module_name, [dirpath])
    module = imp.load_module(full_module_name, fp, pathname, description)
    setattr(dst_module, module_name, module)

    return module


def _load_module_from_dirpath_py3(dirpath, module_name, dst_module_name):
    full_module_name = "{}.{}".format(dst_module_name, module_name)
    if full_module_name in sys.modules:
        return sys.modules[full_module_name]

    import importlib.util
    from importlib._bootstrap_external import PathFinder

    dst_module = sys.modules[dst_module_name]
    loader = PathFinder.find_module(full_module_name, [dirpath])

    spec = importlib.util.spec_from_loader(
        full_module_name, loader, origin=dirpath
    )

    module = importlib.util.module_from_spec(spec)

    if dst_module is not None:
        setattr(dst_module, module_name, module)

    sys.modules[full_module_name] = module

    loader.exec_module(module)

    return module


def load_module_from_dirpath(dirpath, folder_name, dst_module_name):
    if six.PY3:
        module = _load_module_from_dirpath_py3(
            dirpath, folder_name, dst_module_name
        )
    else:
        module = _load_module_from_dirpath_py2(
            dirpath, folder_name, dst_module_name
        )
    return module


sys.modules["openpype_modules"] = __ModuleClass()
sys.modules["openpype_interfaces"] = __ModuleClass()
