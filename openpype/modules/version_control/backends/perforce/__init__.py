"""
Backend for perforce access in OpenPype
"""

import six

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
        from . import api
        from . import backend
    del _typing

    def __getattr__(name: str):
        current_file = pathlib.Path(__file__)
        current_directory = current_file.parent
        for path in current_directory.iterdir():
            if path.stem != name:
                continue

            return importlib.import_module(f"{__package__}.{name}")

        raise AttributeError(f"{__package__} has no attribute named: {name}")

else:
    raise RuntimeError("Version control is not supported on Python2")

__all__ = ("api", "backend")
