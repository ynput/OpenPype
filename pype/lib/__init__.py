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

from .env_tools import (
    env_value_to_bool,
    get_paths_from_environ
)

from .python_module_tools import (
    modules_from_path,
    recursive_bases_from_class,
    classes_from_module
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
    ApplictionExecutableNotFound,
    ApplicationNotFound,
    ApplicationManager,
    PreLaunchHook,
    PostLaunchHook,
    _subprocess
)

from .plugin_tools import (
    filter_pyblish_plugins,
    source_hash
)

from .user_settings import (
    IniSettingRegistry,
    JSONSettingRegistry,
    PypeSettingsRegistry
)

from .path_tools import (
    version_up,
    get_version_from_path,
    get_last_version_from_path
)

from .ffmpeg_utils import (
    get_ffmpeg_tool_path,
    ffprobe_streams
)

terminal = Terminal

__all__ = [
    "env_value_to_bool",
    "get_paths_from_environ",

    "modules_from_path",
    "recursive_bases_from_class",
    "classes_from_module",

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
    "ApplictionExecutableNotFound",
    "ApplicationNotFound",
    "ApplicationManager",
    "PreLaunchHook",
    "PostLaunchHook",

    "filter_pyblish_plugins",
    "source_hash",

    "version_up",
    "get_version_from_path",
    "get_last_version_from_path",

    "ffprobe_streams",
    "get_ffmpeg_tool_path",

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
