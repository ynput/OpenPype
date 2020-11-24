import os
import types
import inspect
import logging

log = logging.getLogger(__name__)


def modules_from_path(folder_path):
    """Get python scripts as modules from a path.

    Arguments:
        path (str): Path to folder containing python scripts.

    Returns:
        List of modules.
    """

    folder_path = os.path.normpath(folder_path)

    modules = []
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
            module.__file__ = full_path

            with open(full_path) as _stream:
                # Execute content and store it to module object
                exec(_stream.read(), module.__dict__)

            modules.append(module)

        except Exception:
            log.warning(
                "Failed to load path: \"{0}\"".format(full_path),
                exc_info=True
            )
            continue

    return modules


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
