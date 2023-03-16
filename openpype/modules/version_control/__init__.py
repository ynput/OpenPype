"""
Package for interfacing with version control systems
"""

_compatible_dcc = True

import six

from .version_control_module import VERSION_CONTROL_MODULE_DIR
from .version_control_module import VersionControlModule

if six.PY3:
    # This is a clever hack to get python to import in a lazy (sensible) way
    # whilst allowing static analysis to work correctly.
    # Effectively this is forcing python to see these sub-packages without
    # importing any packages until they are needed, this also helps
    # avoid triggering potential dependency loops.
    # The module level __getattr__ will handle lazy imports in this syntax:

    # ```
    # import version_control
    # version_control.backends.perforce.sync
    # ```

    import importlib
    import pathlib

    # this is used instead of typing.TYPE_CHECKING as it
    # avoids needing to import the typing module at all:
    _typing = False
    if _typing:
        from typing import Any

        from . import api
        from . import backends
        from . import hosts
        from . import lib
        from . import widgets
    del _typing

    def __getattr__(name):
        # type: (str) -> Any
        current_file = pathlib.Path(__file__)
        current_directory = current_file.parent
        for path in current_directory.iterdir():
            if path.stem != name:
                continue

            try:
                return importlib.import_module("{0}.{1}".format(__package__, name))
            except ImportError as error:
                if "No module named P4API" not in str(error):
                    raise

                global _compatible_dcc
                _compatible_dcc = False

        raise AttributeError("{0} has no attribute named: {0}".format(__package__, name))

else:
    raise RuntimeError("Version control is not supported on Python2")

__all__ = (
    "api",
    "backends",
    "hosts",
    "lib",
    "widgets",
    "VersionControlModule",
    "VERSION_CONTROL_MODULE_DIR",
    "_compatible_dcc"
)
