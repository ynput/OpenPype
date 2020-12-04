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
    ApplicationAction,
    _subprocess
)

from .plugin_tools import (
    filter_pyblish_plugins,
    source_hash,
    get_unique_layer_name,
    get_background_layers
)

from .path_tools import (
    version_up,
    get_version_from_path,
    get_last_version_from_path,
    get_paths_from_environ,
    get_ffmpeg_tool_path
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
    "get_unique_layer_name",
    "get_background_layers",

    "version_up",
    "get_version_from_path",
    "get_last_version_from_path",
    "get_paths_from_environ",
    "get_ffmpeg_tool_path",

    "ffprobe_streams",

    "source_hash",
    "_subprocess"
]
