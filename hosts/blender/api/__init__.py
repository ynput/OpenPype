"""Public API

Anything that isn't defined here is INTERNAL and unreliable for external use.

"""

from .pipeline import (
    install,
    uninstall,
    ls,
    publish,
    containerise,
)

from .plugin import (
    Creator,
    Loader,
)

from .workio import (
    open_file,
    save_file,
    current_file,
    has_unsaved_changes,
    file_extensions,
    work_root,
)

from .lib import (
    lsattr,
    lsattrs,
    read,
    maintained_selection,
    get_selection,
    # unique_name,
)


__all__ = [
    "install",
    "uninstall",
    "ls",
    "publish",
    "containerise",

    "Creator",
    "Loader",

    # Workfiles API
    "open_file",
    "save_file",
    "current_file",
    "has_unsaved_changes",
    "file_extensions",
    "work_root",

    # Utility functions
    "maintained_selection",
    "lsattr",
    "lsattrs",
    "read",
    "get_selection",
    # "unique_name",
]
