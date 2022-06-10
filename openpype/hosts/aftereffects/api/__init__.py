"""Public API

Anything that isn't defined here is INTERNAL and unreliable for external use.

"""

from .launch_logic import (
    get_stub,
    stub,
)

from .pipeline import (
    ls,
    get_asset_settings,
    install,
    uninstall,
    list_instances,
    remove_instance,
    containerise,
    get_context_data,
    update_context_data,
    get_context_title
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
    get_extension_manifest_path
)

from .plugin import (
    AfterEffectsLoader
)


__all__ = [
    # launch_logic
    "get_stub",
    "stub",

    # pipeline
    "ls",
    "get_asset_settings",
    "install",
    "uninstall",
    "list_instances",
    "remove_instance",
    "containerise",
    "get_context_data",
    "update_context_data",
    "get_context_title",

    "file_extensions",
    "has_unsaved_changes",
    "save_file",
    "open_file",
    "current_file",
    "work_root",

    # lib
    "maintained_selection",
    "get_extension_manifest_path",

    # plugin
    "AfterEffectsLoader"
]
