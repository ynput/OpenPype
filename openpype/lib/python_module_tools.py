import os
import sys
import types
import importlib
import inspect
import logging

import six

log = logging.getLogger(__name__)


def import_filepath(filepath, module_name=None):
    """Import python file as python module.

    Python 2 and Python 3 compatibility.

    Args:
        filepath(str): Path to python file.
        module_name(str): Name of loaded module. Only for Python 3. By default
            is filled with filename of filepath.
    """
    if module_name is None:
        module_name = os.path.splitext(os.path.basename(filepath))[0]

    # Make sure it is not 'unicode' in Python 2
    module_name = str(module_name)

    # Prepare module object where content of file will be parsed
    module = types.ModuleType(module_name)

    if six.PY3:
        # Use loader so module has full specs
        module_loader = importlib.machinery.SourceFileLoader(
            module_name, filepath
        )
        module_loader.exec_module(module)
    else:
        # Execute module code and store content to module
        with open(filepath) as _stream:
            # Execute content and store it to module object
            six.exec_(_stream.read(), module.__dict__)

        module.__file__ = filepath
    return module


def modules_from_path(folder_path):
    """Get python scripts as modules from a path.

    Arguments:
        path (str): Path to folder containing python scripts.

    Returns:
        tuple<list, list>: First list contains successfully imported modules
            and second list contains tuples of path and exception.
    """
    crashed = []
    modules = []
    output = (modules, crashed)
    # Just skip and return empty list if path is not set
    if not folder_path:
        return output

    # Do not allow relative imports
    if folder_path.startswith("."):
        log.warning((
            "BUG: Relative paths are not allowed for security reasons. {}"
        ).format(folder_path))
        return output

    folder_path = os.path.normpath(folder_path)

    if not os.path.isdir(folder_path):
        log.warning("Not a directory path: {}".format(folder_path))
        return output

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
            module = import_filepath(full_path, mod_name)
            modules.append((full_path, module))

        except Exception:
            crashed.append((full_path, sys.exc_info()))
            log.warning(
                "Failed to load path: \"{0}\"".format(full_path),
                exc_info=True
            )
            continue

    return output


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
        if not inspect.isclass(obj) or obj is superclass:
            continue

        if issubclass(obj, superclass):
            classes.append(obj)

    return classes


def _import_module_from_dirpath_py2(dirpath, module_name, dst_module_name):
    """Import passed dirpath as python module using `imp`."""
    if dst_module_name:
        full_module_name = "{}.{}".format(dst_module_name, module_name)
        dst_module = sys.modules[dst_module_name]
    else:
        full_module_name = module_name
        dst_module = None

    if full_module_name in sys.modules:
        return sys.modules[full_module_name]

    import imp

    fp, pathname, description = imp.find_module(module_name, [dirpath])
    module = imp.load_module(full_module_name, fp, pathname, description)
    if dst_module is not None:
        setattr(dst_module, module_name, module)

    return module


def _import_module_from_dirpath_py3(dirpath, module_name, dst_module_name):
    """Import passed dirpath as python module using Python 3 modules."""
    if dst_module_name:
        full_module_name = "{}.{}".format(dst_module_name, module_name)
        dst_module = sys.modules[dst_module_name]
    else:
        full_module_name = module_name
        dst_module = None

    # Skip import if is already imported
    if full_module_name in sys.modules:
        return sys.modules[full_module_name]

    import importlib.util
    from importlib._bootstrap_external import PathFinder

    # Find loader for passed path and name
    loader = PathFinder.find_module(full_module_name, [dirpath])

    # Load specs of module
    spec = importlib.util.spec_from_loader(
        full_module_name, loader, origin=dirpath
    )

    # Create module based on specs
    module = importlib.util.module_from_spec(spec)

    # Store module to destination module and `sys.modules`
    # WARNING this mus be done before module execution
    if dst_module is not None:
        setattr(dst_module, module_name, module)

    sys.modules[full_module_name] = module

    # Execute module import
    loader.exec_module(module)

    return module


def import_module_from_dirpath(dirpath, folder_name, dst_module_name=None):
    """Import passed directory as a python module.

    Python 2 and 3 compatible.

    Imported module can be assigned as a child attribute of already loaded
    module from `sys.modules` if has support of `setattr`. That is not default
    behavior of python modules so parent module must be a custom module with
    that ability.

    It is not possible to reimport already cached module. If you need to
    reimport module you have to remove it from caches manually.

    Args:
        dirpath(str): Parent directory path of loaded folder.
        folder_name(str): Folder name which should be imported inside passed
            directory.
        dst_module_name(str): Parent module name under which can be loaded
            module added.
    """
    if six.PY3:
        module = _import_module_from_dirpath_py3(
            dirpath, folder_name, dst_module_name
        )
    else:
        module = _import_module_from_dirpath_py2(
            dirpath, folder_name, dst_module_name
        )
    return module
