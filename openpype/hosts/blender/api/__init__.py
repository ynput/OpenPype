"""Public API

Anything that isn't defined here is INTERNAL and unreliable for external use.

"""

from .pipeline import (
    install,
    uninstall,
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
    get_compress_setting,
    file_extensions,
    work_root,
)

from .lib import (
    ls,
    lsattr,
    lsattrs,
    read,
    maintained_selection,
    maintained_time,
    get_selection,
    # unique_name,
)

from .capture import capture


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
    "get_compress_setting",
    "file_extensions",
    "work_root",

    # Utility functions
    "maintained_selection",
    "maintained_time",
    "lsattr",
    "lsattrs",
    "read",
    "get_selection",
    "capture",
    # "unique_name",
]
