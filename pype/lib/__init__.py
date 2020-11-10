# -*- coding: utf-8 -*-
"""Pype lib module."""

from .deprecated import (
    get_avalon_database,
    set_io_database
)

from .avalon_context import (
    is_latest,
    any_outdated,
    get_asset,
    get_hierarchy,
    get_linked_assets,
    get_latest_version,
    BuildWorkfile
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
    add_tool_to_environment,
    modified_environ,
    pairwise,
    grouper,
    _rreplace,
    version_up,
    _get_host_name,
    get_version_from_path,
    get_last_version_from_path,
    source_hash,
)
from .ffmpeg_utils import ffprobe_streams

__all__ = [
    "get_avalon_database",
    "set_io_database",

    "is_latest",
    "any_outdated",
    "get_asset",
    "get_hierarchy",
    "get_linked_assets",
    "get_latest_version",
    "BuildWorkfile",

    "PypeHook",
    "execute_hook",

    "ApplicationLaunchFailed",
    "launch_application",
    "ApplicationAction",

    "filter_pyblish_plugins",

    "ffprobe_streams"
]
