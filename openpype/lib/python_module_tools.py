import os
import sys
import types
import importlib
import inspect
import logging

log = logging.getLogger(__name__)
PY3 = sys.version_info[0] == 3


def modules_from_path(folder_path):
    """Get python scripts as modules from a path.

    Arguments:
        path (str): Path to folder containing python scripts.
        return_crasher (bool): Crashed module paths with exception info
            will be returned too.

    Returns:
        list, tuple: List of modules when `return_crashed` is False else tuple
            with list of modules at first place and tuple of path and exception
            info at second place.
    """
    crashed = []
    modules = []
    # Just skip and return empty list if path is not set
    if not folder_path:
        return modules

    # Do not allow relative imports
    if folder_path.startswith("."):
        log.warning((
            "BUG: Relative paths are not allowed for security reasons. {}"
        ).format(folder_path))
        return modules

    folder_path = os.path.normpath(folder_path)

    if not os.path.isdir(folder_path):
        log.warning("Not a directory path: {}".format(folder_path))
        return modules

    for filename in os.listdir(folder_path):
        # Ignore files which start with underscore
        if filename.startswith("_"):
            continue

        mod_name, mod_ext = os.path.splitext(filename)
        if not mod_ext == ".py":
            continue

        full_path = os.path.join(folder_path, filename)
        if not os.path.isfile(full_path):
            continue

        try:
            # Prepare module object where content of file will be parsed
            module = types.ModuleType(mod_name)

            if PY3:
                # Use loader so module has full specs
                module_loader = importlib.machinery.SourceFileLoader(
                    mod_name, full_path
                )
                module_loader.exec_module(module)
            else:
                # Execute module code and store content to module
                with open(full_path) as _stream:
                    # Execute content and store it to module object
                    exec(_stream.read(), module.__dict__)

                module.__file__ = full_path

            modules.append((full_path, module))

        except Exception:
            crashed.append((full_path, sys.exc_info()))
            log.warning(
                "Failed to load path: \"{0}\"".format(full_path),
                exc_info=True
            )
            continue

    return modules, crashed


def recursive_bases_from_class(klass):
    """Extract all bases from entered class."""
    result = []
    bases = klass.__bases__
    result.extend(bases)
    for base in bases:
        result.extend(recursive_bases_from_class(base))
    return result


def classes_from_module(superclass, module):
    """Return plug-ins from module

    Arguments:
        superclass (superclass): Superclass of subclasses to look for
        module (types.ModuleType): Imported module from which to
            parse valid Avalon plug-ins.

    Returns:
        List of plug-ins, or empty list if none is found.

    """

    classes = list()
    for name in dir(module):
        # It could be anything at this point
        obj = getattr(module, name)
        if not inspect.isclass(obj):
            continue

        # These are subclassed from nothing, not even `object`
        if not len(obj.__bases__) > 0:
            continue

        # Use string comparison rather than `issubclass`
        # in order to support reloading of this module.
        bases = recursive_bases_from_class(obj)
        if not any(base.__name__ == superclass.__name__ for base in bases):
            continue

        classes.append(obj)
    return classes
