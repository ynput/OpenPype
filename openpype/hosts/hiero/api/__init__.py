from .workio import (
    open_file,
    save_file,
    current_file,
    has_unsaved_changes,
    file_extensions,
    work_root
)

from .pipeline import (
    launch_workfiles_app,
    ls,
    install,
    uninstall,
    reload_config,
    containerise,
    publish,
    maintained_selection,
    parse_container,
    update_container,
    reset_selection
)

from .constants import (
    OPENPYPE_TAG_NAME,
    DEFAULT_SEQUENCE_NAME,
    DEFAULT_BIN_NAME
)

from .lib import (
    flatten,
    get_track_items,
    get_current_project,
    get_current_sequence,
    get_timeline_selection,
    get_current_track,
    get_track_item_tags,
    get_track_openpype_tag,
    set_track_openpype_tag,
    get_track_openpype_data,
    get_track_item_pype_tag,
    set_track_item_pype_tag,
    get_track_item_pype_data,
    get_trackitem_openpype_tag,
    set_trackitem_openpype_tag,
    get_trackitem_openpype_data,
    set_publish_attribute,
    get_publish_attribute,
    imprint,
    get_selected_track_items,
    set_selected_track_items,
    create_nuke_workfile_clips,
    create_bin,
    apply_colorspace_project,
    apply_colorspace_clips,
    is_overlapping,
    get_sequence_pattern_and_padding
)

from .plugin import (
    CreatorWidget,
    Creator,
    PublishClip,
    SequenceLoader,
    ClipLoader
)

__all__ = [
    # avalon pipeline module
    "launch_workfiles_app",
    "ls",
    "install",
    "uninstall",
    "reload_config",
    "containerise",
    "publish",
    "maintained_selection",
    "parse_container",
    "update_container",
    "reset_selection",

    # Workfiles API
    "open_file",
    "save_file",
    "current_file",
    "has_unsaved_changes",
    "file_extensions",
    "work_root",

    # Constants
    "OPENPYPE_TAG_NAME",
    "DEFAULT_SEQUENCE_NAME",
    "DEFAULT_BIN_NAME",

    # Lib functions
    "flatten",
    "get_track_items",
    "get_current_project",
    "get_current_sequence",
    "get_timeline_selection",
    "get_current_track",
    "get_track_item_tags",
    "get_track_openpype_tag",
    "set_track_openpype_tag",
    "get_track_openpype_data",
    "get_trackitem_openpype_tag",
    "set_trackitem_openpype_tag",
    "get_trackitem_openpype_data",
    "set_publish_attribute",
    "get_publish_attribute",
    "imprint",
    "get_selected_track_items",
    "set_selected_track_items",
    "create_nuke_workfile_clips",
    "create_bin",
    "is_overlapping",
    "apply_colorspace_project",
    "apply_colorspace_clips",
    "get_sequence_pattern_and_padding",
    # deprecated
    "get_track_item_pype_tag",
    "set_track_item_pype_tag",
    "get_track_item_pype_data",

    # plugins
    "CreatorWidget",
    "Creator",
    "PublishClip",
    "SequenceLoader",
    "ClipLoader"
]
