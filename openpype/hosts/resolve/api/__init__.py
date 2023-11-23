"""
resolve api
"""
from .utils import (
    get_resolve_module
)

from .pipeline import (
    ResolveHost,
    ls,
    containerise,
    update_container,
    maintained_selection,
    remove_instance,
    list_instances
)

from .lib import (
    maintain_current_timeline,
    publish_clip_color,
    get_project_manager,
    get_current_project,
    get_current_timeline,
    get_any_timeline,
    get_new_timeline,
    create_bin,
    get_media_pool_item,
    create_media_pool_item,
    create_timeline_item,
    get_timeline_item,
    get_video_track_names,
    get_current_timeline_items,
    get_pype_timeline_item_by_name,
    get_timeline_item_pype_tag,
    set_timeline_item_pype_tag,
    imprint,
    set_publish_attribute,
    get_publish_attribute,
    create_compound_clip,
    swap_clips,
    get_pype_clip_metadata,
    set_project_manager_to_folder_name,
    get_otio_clip_instance_data,
    get_reformated_path
)

from .menu import launch_pype_menu

from .plugin import (
    ClipLoader,
    TimelineItemLoader,
    Creator,
    PublishClip
)

from .workio import (
    open_file,
    save_file,
    current_file,
    has_unsaved_changes,
    file_extensions,
    work_root
)

from .testing_utils import TestGUI


bmdvr = None
bmdvf = None

__all__ = [
    "bmdvr",
    "bmdvf",

    # pipeline
    "ResolveHost",
    "ls",
    "containerise",
    "update_container",
    "maintained_selection",
    "remove_instance",
    "list_instances",

    # utils
    "get_resolve_module",

    # lib
    "maintain_current_timeline",
    "publish_clip_color",
    "get_project_manager",
    "get_current_project",
    "get_current_timeline",
    "get_any_timeline",
    "get_new_timeline",
    "create_bin",
    "get_media_pool_item",
    "create_media_pool_item",
    "create_timeline_item",
    "get_timeline_item",
    "get_video_track_names",
    "get_current_timeline_items",
    "get_pype_timeline_item_by_name",
    "get_timeline_item_pype_tag",
    "set_timeline_item_pype_tag",
    "imprint",
    "set_publish_attribute",
    "get_publish_attribute",
    "create_compound_clip",
    "swap_clips",
    "get_pype_clip_metadata",
    "set_project_manager_to_folder_name",
    "get_otio_clip_instance_data",
    "get_reformated_path",

    # menu
    "launch_pype_menu",

    # plugin
    "ClipLoader",
    "TimelineItemLoader",
    "Creator",
    "PublishClip",

    # workio
    "open_file",
    "save_file",
    "current_file",
    "has_unsaved_changes",
    "file_extensions",
    "work_root",

    "TestGUI"
]
