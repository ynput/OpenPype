from .utils import (
    setup,
    get_resolve_module
)

from .pipeline import (
    install,
    uninstall,
    ls,
    containerise,
    publish,
    launch_workfiles_app,
    maintained_selection
)

from .lib import (
    get_project_manager,
    get_current_project,
    get_current_sequence,
    get_current_track_items,
    create_current_sequence_media_bin,
    create_compound_clip,
    swap_clips,
    get_pype_clip_metadata,
    set_project_manager_to_folder_name
)

from .menu import launch_pype_menu

from .plugin import Creator

from .workio import (
    open_file,
    save_file,
    current_file,
    has_unsaved_changes,
    file_extensions,
    work_root
)

bmdvr = None
bmdvf = None

__all__ = [
    # pipeline
    "install",
    "uninstall",
    "ls",
    "containerise",
    "reload_pipeline",
    "publish",
    "launch_workfiles_app",
    "maintained_selection",

    # utils
    "setup",
    "get_resolve_module",

    # lib
    "get_project_manager",
    "get_current_project",
    "get_current_sequence",
    "get_current_track_items",
    "create_current_sequence_media_bin",
    "create_compound_clip",
    "swap_clips",
    "get_pype_clip_metadata",
    "set_project_manager_to_folder_name",

    # menu
    "launch_pype_menu",

    # plugin
    "Creator",

    # workio
    "open_file",
    "save_file",
    "current_file",
    "has_unsaved_changes",
    "file_extensions",
    "work_root",

    # singleton with black magic resolve module
    "bmdvr",
    "bmdvf"
]
