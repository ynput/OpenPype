# -*- coding: utf-8 -*-
# flake8: noqa E402
"""OpenPype lib functions."""
# add vendor to sys path based on Python version
import sys
import os
import site
from openpype import PACKAGE_DIR

# Add Python version specific vendor folder
python_version_dir = os.path.join(
    PACKAGE_DIR, "vendor", "python", "python_{}".format(sys.version[0])
)
# Prepend path in sys paths
sys.path.insert(0, python_version_dir)
site.addsitedir(python_version_dir)


from .events import (
    emit_event,
    register_event_callback
)

from .vendor_bin_utils import (
    ToolNotFoundError,
    find_executable,
    get_vendor_bin_path,
    get_oiio_tools_path,
    get_oiio_tool_args,
    get_ffmpeg_tool_path,
    get_ffmpeg_tool_args,
    is_oiio_supported,
)

from .attribute_definitions import (
    AbstractAttrDef,

    UIDef,
    UISeparatorDef,
    UILabelDef,

    UnknownDef,
    NumberDef,
    TextDef,
    EnumDef,
    BoolDef,
    FileDef,
    FileDefItem,
)

from .env_tools import (
    env_value_to_bool,
    get_paths_from_environ,
)

from .terminal import Terminal
from .execute import (
    get_ayon_launcher_args,
    get_openpype_execute_args,
    get_linux_launcher_args,
    execute,
    run_subprocess,
    run_detached_process,
    run_ayon_launcher_process,
    run_openpype_process,
    clean_envs_for_openpype_process,
    path_to_subprocess_arg,
    CREATE_NO_WINDOW
)
from .log import (
    Logger,
)

from .path_templates import (
    merge_dict,
    TemplateMissingKey,
    TemplateUnsolved,
    StringTemplate,
    TemplatesDict,
    FormatObject,
)

from .dateutils import (
    get_datetime_data,
    get_timestamp,
    get_formatted_current_time
)

from .python_module_tools import (
    import_filepath,
    modules_from_path,
    recursive_bases_from_class,
    classes_from_module,
    import_module_from_dirpath,
    is_func_signature_supported,
)

from .profiles_filtering import (
    compile_list_of_regexes,
    filter_profiles
)

from .transcoding import (
    get_transcode_temp_directory,
    should_convert_for_ffmpeg,
    convert_for_ffmpeg,
    convert_input_paths_for_ffmpeg,
    get_ffprobe_data,
    get_ffprobe_streams,
    get_ffmpeg_codec_args,
    get_ffmpeg_format_args,
    convert_ffprobe_fps_value,
    convert_ffprobe_fps_to_float,
    get_rescaled_command_arguments,
)

from .local_settings import (
    IniSettingRegistry,
    JSONSettingRegistry,
    OpenPypeSecureRegistry,
    OpenPypeSettingsRegistry,
    get_local_site_id,
    change_openpype_mongo_url,
    get_openpype_username,
    is_admin_password_required
)

from .applications import (
    ApplicationLaunchFailed,
    ApplictionExecutableNotFound,
    ApplicationNotFound,
    ApplicationManager,

    PreLaunchHook,
    PostLaunchHook,

    EnvironmentPrepData,
    prepare_app_environments,
    prepare_context_environments,
    get_app_environments_for_context,
    apply_project_environments_value
)

from .plugin_tools import (
    prepare_template_data,
    source_hash,
)

from .path_tools import (
    format_file_size,
    collect_frames,
    create_hard_link,
    version_up,
    get_version_from_path,
    get_last_version_from_path,
)

from .openpype_version import (
    op_version_control_available,
    get_openpype_version,
    get_build_version,
    get_expected_version,
    is_running_from_build,
    is_running_staging,
    is_current_version_studio_latest,
    is_current_version_higher_than_expected
)


from .connections import (
    requests_get,
    requests_post
)

terminal = Terminal

__all__ = [
    "emit_event",
    "register_event_callback",

    "get_ayon_launcher_args",
    "get_openpype_execute_args",
    "get_linux_launcher_args",
    "execute",
    "run_subprocess",
    "run_detached_process",
    "run_ayon_launcher_process",
    "run_openpype_process",
    "clean_envs_for_openpype_process",
    "path_to_subprocess_arg",
    "CREATE_NO_WINDOW",

    "env_value_to_bool",
    "get_paths_from_environ",

    "ToolNotFoundError",
    "find_executable",
    "get_vendor_bin_path",
    "get_oiio_tools_path",
    "get_oiio_tool_args",
    "get_ffmpeg_tool_path",
    "get_ffmpeg_tool_args",
    "is_oiio_supported",

    "AbstractAttrDef",

    "UIDef",
    "UISeparatorDef",
    "UILabelDef",

    "UnknownDef",
    "NumberDef",
    "TextDef",
    "EnumDef",
    "BoolDef",
    "FileDef",
    "FileDefItem",

    "import_filepath",
    "modules_from_path",
    "recursive_bases_from_class",
    "classes_from_module",
    "import_module_from_dirpath",
    "is_func_signature_supported",

    "get_transcode_temp_directory",
    "should_convert_for_ffmpeg",
    "convert_for_ffmpeg",
    "convert_input_paths_for_ffmpeg",
    "get_ffprobe_data",
    "get_ffprobe_streams",
    "get_ffmpeg_codec_args",
    "get_ffmpeg_format_args",
    "convert_ffprobe_fps_value",
    "convert_ffprobe_fps_to_float",
    "get_rescaled_command_arguments",

    "IniSettingRegistry",
    "JSONSettingRegistry",
    "OpenPypeSecureRegistry",
    "OpenPypeSettingsRegistry",
    "get_local_site_id",
    "change_openpype_mongo_url",
    "get_openpype_username",
    "is_admin_password_required",

    "ApplicationLaunchFailed",
    "ApplictionExecutableNotFound",
    "ApplicationNotFound",
    "ApplicationManager",
    "PreLaunchHook",
    "PostLaunchHook",
    "EnvironmentPrepData",
    "prepare_app_environments",
    "prepare_context_environments",
    "get_app_environments_for_context",
    "apply_project_environments_value",

    "compile_list_of_regexes",

    "filter_profiles",

    "prepare_template_data",
    "source_hash",

    "format_file_size",
    "collect_frames",
    "create_hard_link",
    "version_up",
    "get_version_from_path",
    "get_last_version_from_path",

    "merge_dict",
    "TemplateMissingKey",
    "TemplateUnsolved",
    "StringTemplate",
    "TemplatesDict",
    "FormatObject",

    "terminal",

    "get_datetime_data",
    "get_formatted_current_time",

    "Logger",

    "op_version_control_available",
    "get_openpype_version",
    "get_build_version",
    "get_expected_version",
    "is_running_from_build",
    "is_running_staging",
    "is_current_version_studio_latest",

    "requests_get",
    "requests_post"
]
