"""
OpenPype Autodesk Flame api
"""
from .constants import (
    COLOR_MAP,
    MARKER_NAME,
    MARKER_COLOR,
    MARKER_DURATION,
    MARKER_PUBLISH_DEFAULT
)
from .lib import (
    CTX,
    FlameAppFramework,
    get_project_manager,
    get_current_project,
    get_current_sequence,
    create_bin,
    create_segment_data_marker,
    get_segment_data_marker,
    set_segment_data_marker,
    set_publish_attribute,
    get_publish_attribute,
    get_sequence_segments,
    maintained_segment_selection,
    reset_segment_selection,
    get_segment_attributes,
    get_clips_in_reels,
    get_reformated_filename,
    get_frame_from_filename,
    get_padding_from_filename,
    maintained_object_duplication,
    get_clip_segment
)
from .utils import (
    setup,
    get_flame_version,
    get_flame_install_root
)
from .pipeline import (
    install,
    uninstall,
    ls,
    containerise,
    update_container,
    remove_instance,
    list_instances,
    imprint,
    maintained_selection
)
from .menu import (
    FlameMenuProjectConnect,
    FlameMenuTimeline
)
from .plugin import (
    Creator,
    PublishableClip,
    ClipLoader,
    OpenClipSolver

)
from .workio import (
    open_file,
    save_file,
    current_file,
    has_unsaved_changes,
    file_extensions,
    work_root
)
from .render_utils import (
    export_clip,
    get_preset_path_by_xml_name,
    modify_preset_file
)
from .batch_utils import (
    create_batch
)

__all__ = [
    # constants
    "COLOR_MAP",
    "MARKER_NAME",
    "MARKER_COLOR",
    "MARKER_DURATION",
    "MARKER_PUBLISH_DEFAULT",

    # lib
    "CTX",
    "FlameAppFramework",
    "get_project_manager",
    "get_current_project",
    "get_current_sequence",
    "create_bin",
    "create_segment_data_marker",
    "get_segment_data_marker",
    "set_segment_data_marker",
    "set_publish_attribute",
    "get_publish_attribute",
    "get_sequence_segments",
    "maintained_segment_selection",
    "reset_segment_selection",
    "get_segment_attributes",
    "get_clips_in_reels",
    "get_reformated_filename",
    "get_frame_from_filename",
    "get_padding_from_filename",
    "maintained_object_duplication",
    "get_clip_segment",

    # pipeline
    "install",
    "uninstall",
    "ls",
    "containerise",
    "update_container",
    "reload_pipeline",
    "maintained_selection",
    "remove_instance",
    "list_instances",
    "imprint",
    "maintained_selection",

    # utils
    "setup",
    "get_flame_version",
    "get_flame_install_root",

    # menu
    "FlameMenuProjectConnect",
    "FlameMenuTimeline",

    # plugin
    "Creator",
    "PublishableClip",
    "ClipLoader",
    "OpenClipSolver",

    # workio
    "open_file",
    "save_file",
    "current_file",
    "has_unsaved_changes",
    "file_extensions",
    "work_root",

    # render utils
    "export_clip",
    "get_preset_path_by_xml_name",
    "modify_preset_file",
    

    # batch utils
    "create_batch"
]
