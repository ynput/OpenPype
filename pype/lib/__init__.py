# -*- coding: utf-8 -*-
"""Pype module API."""

from .terminal import Terminal
from .execute import execute
from .log import PypeLogger, timeit
from .mongo import (
    decompose_url,
    compose_url,
    get_default_components
)
from .anatomy import Anatomy

from .config import (
    get_datetime_data,
    load_json,
    collect_json_from_path,
    get_presets,
    get_init_presets,
    update_dict
)

from .path_tools import (
    version_up,
    get_version_from_path,
    get_last_version_from_path,
    get_paths_from_environ,
    get_ffmpeg_tool_path
)
from .ffmpeg_utils import ffprobe_streams
from .plugin_tools import filter_pyblish_plugins, source_hash
from .applications import (
    ApplicationLaunchFailed,
    launch_application,
    ApplicationAction,
    _subprocess
)
from .hooks import PypeHook, execute_hook
from .avalon_context import (
    is_latest,
    any_outdated,
    get_asset,
    get_hierarchy,
    get_linked_assets,
    get_latest_version,
    BuildWorkfile
)
from .deprecated import (
    get_avalon_database,
    set_io_database
)

from .user_settings import IniSettingRegistry
from .user_settings import JSONSettingRegistry
from .user_settings import PypeSettingsRegistry

"""Pype lib module."""


terminal = Terminal

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

    "version_up",
    "get_version_from_path",
    "get_last_version_from_path",
    "get_paths_from_environ",
    "get_ffmpeg_tool_path",

    "ffprobe_streams",

    "source_hash",
    "_subprocess",

    "terminal",
    "Anatomy",
    "get_datetime_data",
    "load_json",
    "collect_json_from_path",
    "get_presets",
    "get_init_presets",
    "update_dict",
    "execute",
    "PypeLogger",
    "decompose_url",
    "compose_url",
    "get_default_components",
    "IniSettingRegistry",
    "JSONSettingRegistry",
    "PypeSettingsRegistry",
    "timeit"
]
