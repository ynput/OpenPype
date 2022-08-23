from .pipeline import (
    install,
    uninstall,

    ls,
    containerise,
)

from .plugin import (
    Creator,
)

from .workio import (
    open_file,
    save_file,
    current_file,
    has_unsaved_changes,
    file_extensions,
    work_root
)

from .lib import (
    lsattr,
    lsattrs,
    read,

    maintained_selection
)


__all__ = [
    "install",
    "uninstall",

    "ls",
    "containerise",

    "Creator",

    # Workfiles API
    "open_file",
    "save_file",
    "current_file",
    "has_unsaved_changes",
    "file_extensions",
    "work_root",

    # Utility functions
    "lsattr",
    "lsattrs",
    "read",

    "maintained_selection"
]

# Backwards API compatibility
open = open_file
save = save_file
