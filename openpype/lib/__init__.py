# -*- coding: utf-8 -*-
# flake8: noqa E402
"""Pype module API."""
# add vendor to sys path based on Python version
import sys
import os
import site

# Add Python version specific vendor folder
python_version_dir = os.path.join(
    os.getenv("OPENPYPE_REPOS_ROOT", ""),
    "openpype", "vendor", "python", "python_{}".format(sys.version[0])
)
# Prepend path in sys paths
sys.path.insert(0, python_version_dir)
site.addsitedir(python_version_dir)


from .events import (
    emit_event,
    register_event_callback
)

from .vendor_bin_utils import (
    find_executable,
    get_vendor_bin_path,
    get_oiio_tools_path,
    get_ffmpeg_tool_path,
    is_oiio_supported
)

from .attribute_definitions import (
    AbtractAttrDef,

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
    get_openpype_execute_args,
    get_pype_execute_args,
    get_linux_launcher_args,
    execute,
    run_subprocess,
    run_detached_process,
    run_openpype_process,
    clean_envs_for_openpype_process,
    path_to_subprocess_arg,
    CREATE_NO_WINDOW
)
from .log import PypeLogger, timeit

from .path_templates import (
    merge_dict,
    TemplateMissingKey,
    TemplateUnsolved,
    StringTemplate,
    TemplatesDict,
    FormatObject,
)

from .mongo import (
    get_default_components,
    validate_mongo_connection,
    OpenPypeMongoConnection
)
from .anatomy import (
    Anatomy
)

from .config import (
    get_datetime_data,
    get_formatted_current_time
)

from .python_module_tools import (
    import_filepath,
    modules_from_path,
    recursive_bases_from_class,
    classes_from_module,
    import_module_from_dirpath
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
)
from .avalon_context import (
    CURRENT_DOC_SCHEMAS,
    PROJECT_NAME_ALLOWED_SYMBOLS,
    PROJECT_NAME_REGEX,
    create_project,
    is_latest,
    any_outdated,
    get_asset,
    get_hierarchy,
    get_linked_assets,
    get_latest_version,
    get_system_general_anatomy_data,

    get_workfile_template_key,
    get_workfile_template_key_from_context,
    get_workdir_data,
    get_workdir,
    get_workdir_with_workdir_data,
    get_last_workfile_with_version,
    get_last_workfile,

    create_workfile_doc,
    save_workfile_data_to_doc,
    get_workfile_doc,

    BuildWorkfile,

    get_creator_by_name,

    get_custom_workfile_template,

    change_timer_to_current_context,

    get_custom_workfile_template_by_context,
    get_custom_workfile_template_by_string_context,
    get_custom_workfile_template
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
    TaskNotSetError,
    get_subset_name,
    get_subset_name_with_asset_doc,
    prepare_template_data,
    filter_pyblish_plugins,
    set_plugin_attributes_from_settings,
    source_hash,
    get_unique_layer_name,
    get_background_layers,
)

from .path_tools import (
    create_hard_link,
    version_up,
    get_version_from_path,
    get_last_version_from_path,
    create_project_folders,
    create_workdir_extra_folders,
    get_project_basic_paths,
)

from .editorial import (
    is_overlapping_otio_ranges,
    otio_range_to_frame_range,
    otio_range_with_handles,
    convert_to_padded_path,
    trim_media_range,
    range_from_frames,
    frames_to_secons,
    frames_to_timecode,
    make_sequence_collection
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

    "find_executable",
    "get_openpype_execute_args",
    "get_pype_execute_args",
    "get_linux_launcher_args",
    "execute",
    "run_subprocess",
    "run_detached_process",
    "run_openpype_process",
    "clean_envs_for_openpype_process",
    "path_to_subprocess_arg",
    "CREATE_NO_WINDOW",

    "env_value_to_bool",
    "get_paths_from_environ",

    "get_vendor_bin_path",
    "get_oiio_tools_path",
    "get_ffmpeg_tool_path",
    "is_oiio_supported",

    "AbtractAttrDef",

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

    "get_transcode_temp_directory",
    "should_convert_for_ffmpeg",
    "convert_for_ffmpeg",
    "convert_input_paths_for_ffmpeg",
    "get_ffprobe_data",
    "get_ffprobe_streams",
    "get_ffmpeg_codec_args",
    "get_ffmpeg_format_args",
    "convert_ffprobe_fps_value",

    "CURRENT_DOC_SCHEMAS",
    "PROJECT_NAME_ALLOWED_SYMBOLS",
    "PROJECT_NAME_REGEX",
    "create_project",
    "is_latest",
    "any_outdated",
    "get_asset",
    "get_hierarchy",
    "get_linked_assets",
    "get_latest_version",
    "get_system_general_anatomy_data",

    "get_workfile_template_key",
    "get_workfile_template_key_from_context",
    "get_workdir_data",
    "get_workdir",
    "get_workdir_with_workdir_data",
    "get_last_workfile_with_version",
    "get_last_workfile",

    "create_workfile_doc",
    "save_workfile_data_to_doc",
    "get_workfile_doc",

    "BuildWorkfile",

    "get_creator_by_name",

    "change_timer_to_current_context",

    "get_custom_workfile_template_by_context",
    "get_custom_workfile_template_by_string_context",
    "get_custom_workfile_template",

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

    "TaskNotSetError",
    "get_subset_name",
    "get_subset_name_with_asset_doc",
    "filter_pyblish_plugins",
    "set_plugin_attributes_from_settings",
    "source_hash",
    "get_unique_layer_name",
    "get_background_layers",

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

    "Anatomy",

    "get_datetime_data",
    "get_formatted_current_time",

    "PypeLogger",
    "get_default_components",
    "validate_mongo_connection",
    "OpenPypeMongoConnection",

    "timeit",

    "is_overlapping_otio_ranges",
    "otio_range_with_handles",
    "convert_to_padded_path",
    "otio_range_to_frame_range",
    "trim_media_range",
    "range_from_frames",
    "frames_to_secons",
    "frames_to_timecode",
    "make_sequence_collection",
    "create_project_folders",
    "create_workdir_extra_folders",
    "get_project_basic_paths",

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
