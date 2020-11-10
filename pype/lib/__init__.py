# -*- coding: utf-8 -*-
"""Pype lib module."""

from .deprecated import (
    get_avalon_database,
    set_io_database
)

from .hooks import PypeHook, execute_hook

from .applications import (
    ApplicationLaunchFailed,
    launch_application,
    ApplicationAction
)

from .plugin_tools import filter_pyblish_plugins

from .lib_old import (
    _subprocess,
    get_paths_from_environ,
    get_ffmpeg_tool_path,
    get_hierarchy,
    add_tool_to_environment,
    is_latest,
    any_outdated,
    _rreplace,
    version_up,
    switch_item,
    get_asset,
    get_version_from_path,
    get_last_version_from_path,
    get_subsets,
    get_linked_assets,
    BuildWorkfile,
    ffprobe_streams,
    source_hash,
    get_latest_version
)

__all__ = [
    "get_avalon_database",
    "set_io_database",

    "PypeHook",
    "execute_hook",

    "ApplicationLaunchFailed",
    "launch_application",
    "ApplicationAction",

    "filter_pyblish_plugins"
]
