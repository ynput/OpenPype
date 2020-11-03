# -*- coding: utf-8 -*-
"""Pype lib module."""

from .deprecated import (
    get_avalon_database,
    set_io_database
)
from .lib_old import (
    _subprocess,
    get_paths_from_environ,
    get_ffmpeg_tool_path,
    get_hierarchy,
    add_tool_to_environment,
    modified_environ,
    pairwise,
    grouper,
    is_latest,
    any_outdated,
    _rreplace,
    version_up,
    switch_item,
    _get_host_name,
    get_asset,
    get_project,
    get_version_from_path,
    get_last_version_from_path,
    get_subsets,
    CustomNone,
    get_linked_assets,
    map_subsets_by_family,
    BuildWorkfile,
    ffprobe_streams,
    source_hash,
    get_latest_version,
    ApplicationLaunchFailed,
    launch_application,
    ApplicationAction
    )

from .hooks import PypeHook, execute_hook
from .plugin_tools import filter_pyblish_plugins

__all__ = [
    "get_avalon_database",
    "set_io_database",

    "PypeHook",
    "execute_hook",

    "filter_pyblish_plugins"
]
