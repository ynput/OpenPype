# -*- coding: utf-8 -*-
"""Pype module API."""

from .terminal import Terminal
from .execute import (
    execute,
    run_subprocess
)
from .log import PypeLogger, timeit
from .mongo import (
    decompose_url,
    compose_url,
    get_default_components,
    PypeMongoConnection
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

from .applications import (
    ApplicationLaunchFailed,
    ApplictionExecutableNotFound,
    ApplicationNotFound,
    ApplicationManager,
    PreLaunchHook,
    PostLaunchHook
)

from .plugin_tools import (
    filter_pyblish_plugins,
    source_hash,
    get_unique_layer_name,
    get_background_layers,
    oiio_supported,
    decompress,
    get_decompress_dir,
    should_decompress
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
    "execute",
    "run_subprocess",

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

    "ApplicationLaunchFailed",
    "ApplictionExecutableNotFound",
    "ApplicationNotFound",
    "ApplicationManager",
    "PreLaunchHook",
    "PostLaunchHook",

    "filter_pyblish_plugins",
    "source_hash",
    "get_unique_layer_name",
    "get_background_layers",
    "oiio_supported",
    "decompress",
    "get_decompress_dir",
    "should_decompress",

    "version_up",
    "get_version_from_path",
    "get_last_version_from_path",

    "ffprobe_streams",
    "get_ffmpeg_tool_path",

    "terminal",
    "Anatomy",
    "get_datetime_data",
    "load_json",
    "collect_json_from_path",
    "get_presets",
    "get_init_presets",
    "update_dict",

    "PypeLogger",
    "decompose_url",
    "compose_url",
    "get_default_components",
    "PypeMongoConnection",

    "IniSettingRegistry",
    "JSONSettingRegistry",
    "PypeSettingsRegistry",
    "timeit"
]
