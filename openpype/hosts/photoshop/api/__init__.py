"""Public API

Anything that isn't defined here is INTERNAL and unreliable for external use.

"""

from .launch_logic import stub

from .pipeline import (
    ls,
    list_instances,
    remove_instance,
    install,
    uninstall,
    containerise,
    get_context_data,
    update_context_data,
    get_context_title
)
from .plugin import (
    PhotoshopLoader,
    get_unique_layer_name
)
from .workio import (
    file_extensions,
    has_unsaved_changes,
    save_file,
    open_file,
    current_file,
    work_root,
)

from .lib import (
    maintained_selection,
    maintained_visibility
)

__all__ = [
    # launch_logic
    "stub",

    # pipeline
    "ls",
    "list_instances",
    "remove_instance",
    "install",
    "uninstall",
    "containerise",
    "get_context_data",
    "update_context_data",
    "get_context_title",

    # Plugin
    "PhotoshopLoader",
    "get_unique_layer_name",

    # workfiles
    "file_extensions",
    "has_unsaved_changes",
    "save_file",
    "open_file",
    "current_file",
    "work_root",

    # lib
    "maintained_selection",
    "maintained_visibility",
]
