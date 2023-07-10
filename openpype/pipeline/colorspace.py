from copy import deepcopy
import re
import os
import json
import platform
import contextlib
import tempfile
from openpype import PACKAGE_DIR
from openpype.settings import get_project_settings
from openpype.lib import (
    StringTemplate,
    run_openpype_process,
    Logger
)
from openpype.pipeline import Anatomy

log = Logger.get_logger(__name__)


class CashedData:
    remapping = None


@contextlib.contextmanager
def _make_temp_json_file():
    """Wrapping function for json temp file
    """
    try:
        # Store dumped json to temporary file
        temporary_json_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        temporary_json_file.close()
        temporary_json_filepath = temporary_json_file.name.replace(
            "\\", "/"
        )

        yield temporary_json_filepath

    except IOError as _error:
        raise IOError(
            "Unable to create temp json file: {}".format(
                _error
            )
        )

    finally:
        # Remove the temporary json
        os.remove(temporary_json_filepath)


def get_ocio_config_script_path():
    """Get path to ocio wrapper script

    Returns:
        str: path string
    """
    return os.path.normpath(
        os.path.join(
            PACKAGE_DIR,
            "scripts",
            "ocio_wrapper.py"
        )
    )


def get_imageio_colorspace_from_filepath(
    path, host_name, project_name,
    config_data=None, file_rules=None,
    project_settings=None,
    validate=True
):
    """Get colorspace name from filepath

    ImageIO Settings file rules are tested for matching rule.

    Args:
        path (str): path string, file rule pattern is tested on it
        host_name (str): host name
        project_name (str): project name
        config_data (dict, optional): config path and template in dict.
                                      Defaults to None.
        file_rules (dict, optional): file rule data from settings.
                                     Defaults to None.
        project_settings (dict, optional): project settings. Defaults to None.
        validate (bool, optional): should resulting colorspace be validated
                                   with config file? Defaults to True.

    Returns:
        str: name of colorspace
    """
    if not any([config_data, file_rules]):
        project_settings = project_settings or get_project_settings(
            project_name
        )
        config_data = get_imageio_config(
            project_name, host_name, project_settings)

        # in case host color management is not enabled
        if not config_data:
            return None

        file_rules = get_imageio_file_rules(
            project_name, host_name, project_settings)

    # match file rule from path
    colorspace_name = None
    for _frule_name, file_rule in file_rules.items():
        pattern = file_rule["pattern"]
        extension = file_rule["ext"]
        ext_match = re.match(
            r".*(?=.{})".format(extension), path
        )
        file_match = re.search(
            pattern, path
        )

        if ext_match and file_match:
            colorspace_name = file_rule["colorspace"]

    if not colorspace_name:
        log.info("No imageio file rule matched input path: '{}'".format(
            path
        ))
        return None

    # validate matching colorspace with config
    if validate and config_data:
        validate_imageio_colorspace_in_config(
            config_data["path"], colorspace_name)

    return colorspace_name


def get_colorspace_from_filepath(config_path, filepath):
    """Get colorspace from file path wrapper.

    Wrapper function for getting colorspace from file path.

    Args:
        config_path (str): path leading to config.ocio file
        filepath (str): path leading to a file

    Returns:
        Any[str, None]: matching colorspace name
    """
    if not compatibility_check():
        # python environment is not compatible with PyOpenColorIO
        # needs to be run in subprocess
        result_data = get_wrapped_with_subprocess(
            "colorspace", "get_colorspace_from_filepath",
            config_path=config_path,
            filepath=filepath
        )
        if result_data:
            return result_data[0]

    from openpype.scripts.ocio_wrapper import _get_colorspace_from_filepath

    result_data = _get_colorspace_from_filepath(config_path, filepath)

    if result_data:
        return result_data[0]


def parse_colorspace_from_filepath(
    path, host_name, project_name,
    config_data=None,
    project_settings=None
):
    """Parse colorspace name from filepath

    An input path can have colorspace name used as part of name
    or as folder name.

    Args:
        path (str): path string
        host_name (str): host name
        project_name (str): project name
        config_data (dict, optional): config path and template in dict.
                                      Defaults to None.
        project_settings (dict, optional): project settings. Defaults to None.

    Returns:
        str: name of colorspace
    """
    if not config_data:
        project_settings = project_settings or get_project_settings(
            project_name
        )
        config_data = get_imageio_config(
            project_name, host_name, project_settings)

    config_path = config_data["path"]

    # match file rule from path
    colorspace_name = None
    colorspaces = get_ocio_config_colorspaces(config_path)
    for colorspace_key in colorspaces:
        # check underscored variant of colorspace name
        # since we are reformatting it in integrate.py
        if colorspace_key.replace(" ", "_") in path:
            colorspace_name = colorspace_key
            break
        if colorspace_key in path:
            colorspace_name = colorspace_key
            break

    if not colorspace_name:
        log.info("No matching colorspace in config '{}' for path: '{}'".format(
            config_path, path
        ))
        return None

    return colorspace_name


def validate_imageio_colorspace_in_config(config_path, colorspace_name):
    """Validator making sure colorspace name is used in config.ocio

    Args:
        config_path (str): path leading to config.ocio file
        colorspace_name (str): tested colorspace name

    Raises:
        KeyError: missing colorspace name

    Returns:
        bool: True if exists
    """
    colorspaces = get_ocio_config_colorspaces(config_path)
    if colorspace_name not in colorspaces:
        raise KeyError(
            "Missing colorspace '{}' in config file '{}'".format(
                colorspace_name, config_path)
        )
    return True


# TODO: remove this in future - backward compatibility
def get_data_subprocess(config_path, data_type):
    """[Deprecated] Get data via subprocess

    Wrapper for Python 2 hosts.

    Args:
        config_path (str): path leading to config.ocio file
    """
    with _make_temp_json_file() as tmp_json_path:
        # Prepare subprocess arguments
        args = [
            "run", get_ocio_config_script_path(),
            "config", data_type,
            "--in_path", config_path,
            "--out_path", tmp_json_path
        ]
        log.info("Executing: {}".format(" ".join(args)))

        process_kwargs = {
            "logger": log
        }

        run_openpype_process(*args, **process_kwargs)

        # return all colorspaces
        return_json_data = open(tmp_json_path).read()
        return json.loads(return_json_data)


def get_wrapped_with_subprocess(command_group, command, **kwargs):
    """Get data via subprocess

    Wrapper for Python 2 hosts.

    Args:
        command_group (str): command group name
        command (str): command name
        **kwargs: command arguments

    Returns:
        Any[dict, None]: data
    """
    with _make_temp_json_file() as tmp_json_path:
        # Prepare subprocess arguments
        args = [
            "run", get_ocio_config_script_path(),
            command_group, command
        ]

        for key_, value_ in kwargs.items():
            args.extend(("--{}".format(key_), value_))

        args.append("--out_path")
        args.append(tmp_json_path)

        log.info("Executing: {}".format(" ".join(args)))

        process_kwargs = {
            "logger": log
        }

        run_openpype_process(*args, **process_kwargs)

        # return all colorspaces
        return_json_data = open(tmp_json_path).read()
        return json.loads(return_json_data)


def compatibility_check():
    """Making sure PyOpenColorIO is importable"""
    try:
        import PyOpenColorIO  # noqa: F401
    except ImportError:
        return False
    return True


def get_ocio_config_colorspaces(config_path):
    """Get all colorspace data

    Wrapper function for aggregating all names and its families.
    Families can be used for building menu and submenus in gui.

    Args:
        config_path (str): path leading to config.ocio file

    Returns:
        dict: colorspace and family in couple
    """
    if not compatibility_check():
        # python environment is not compatible with PyOpenColorIO
        # needs to be run in subprocess
        return get_wrapped_with_subprocess(
            "config", "get_colorspace", in_path=config_path
        )

    from openpype.scripts.ocio_wrapper import _get_colorspace_data

    return _get_colorspace_data(config_path)


# TODO: remove this in future - backward compatibility
def get_colorspace_data_subprocess(config_path):
    """[Deprecated] Get colorspace data via subprocess

    Wrapper for Python 2 hosts.

    Args:
        config_path (str): path leading to config.ocio file

    Returns:
        dict: colorspace and family in couple
    """
    return get_wrapped_with_subprocess(
        "config", "get_colorspace", in_path=config_path
    )


def get_ocio_config_views(config_path):
    """Get all viewer data

    Wrapper function for aggregating all display and related viewers.
    Key can be used for building gui menu with submenus.

    Args:
        config_path (str): path leading to config.ocio file

    Returns:
        dict: `display/viewer` and viewer data
    """
    if not compatibility_check():
        # python environment is not compatible with PyOpenColorIO
        # needs to be run in subprocess
        return get_wrapped_with_subprocess(
            "config", "get_views", in_path=config_path
        )

    from openpype.scripts.ocio_wrapper import _get_views_data

    return _get_views_data(config_path)


# TODO: remove this in future - backward compatibility
def get_views_data_subprocess(config_path):
    """[Deprecated] Get viewers data via subprocess

    Wrapper for Python 2 hosts.

    Args:
        config_path (str): path leading to config.ocio file

    Returns:
        dict: `display/viewer` and viewer data
    """
    return get_wrapped_with_subprocess(
        "config", "get_views", in_path=config_path
    )


def get_imageio_config(
    project_name,
    host_name,
    project_settings=None,
    anatomy_data=None,
    anatomy=None
):
    """Returns config data from settings

    Config path is formatted in `path` key
    and original settings input is saved into `template` key.

    Args:
        project_name (str): project name
        host_name (str): host name
        project_settings (Optional[dict]): Project settings.
        anatomy_data (Optional[dict]): anatomy formatting data.
        anatomy (Optional[Anatomy]): Anatomy object.

    Returns:
        dict: config path data or empty dict
    """
    project_settings = project_settings or get_project_settings(project_name)
    anatomy = anatomy or Anatomy(project_name)

    if not anatomy_data:
        from openpype.pipeline.context_tools import (
            get_template_data_from_session)
        anatomy_data = get_template_data_from_session()

    formatting_data = deepcopy(anatomy_data)

    # Add project roots to anatomy data
    formatting_data["root"] = anatomy.roots
    formatting_data["platform"] = platform.system().lower()

    # Get colorspace settings
    imageio_global, imageio_host = _get_imageio_settings(
        project_settings, host_name)

    # Host 'ocio_config' is optional
    host_ocio_config = imageio_host.get("ocio_config") or {}

    # Global color management must be enabled to be able to use host settings
    activate_color_management = imageio_global.get(
        "activate_global_color_management")
    # TODO: remove this in future - backward compatibility
    # For already saved overrides from previous version look for 'enabled'
    #   on host settings.
    if activate_color_management is None:
        activate_color_management = host_ocio_config.get("enabled", False)

    if not activate_color_management:
        # if global settings are disabled return empty dict because
        # it is expected that no colorspace management is needed
        log.info("Colorspace management is disabled globally.")
        return {}

    # Check if host settings group is having 'activate_host_color_management'
    # - if it does not have activation key then default it to True so it uses
    #       global settings
    # This is for backward compatibility.
    # TODO: in future rewrite this to be more explicit
    activate_host_color_management = imageio_host.get(
        "activate_host_color_management")

    # TODO: remove this in future - backward compatibility
    if activate_host_color_management is None:
        activate_host_color_management = host_ocio_config.get("enabled", False)

    if not activate_host_color_management:
        # if host settings are disabled return False because
        # it is expected that no colorspace management is needed
        log.info(
            "Colorspace management for host '{}' is disabled.".format(
                host_name)
        )
        return {}

    # get config path from either global or host settings
    # depending on override flag
    # TODO: in future rewrite this to be more explicit
    override_global_config = host_ocio_config.get("override_global_config")
    if override_global_config is None:
        # for already saved overrides from previous version
        # TODO: remove this in future - backward compatibility
        override_global_config = host_ocio_config.get("enabled")

    if override_global_config:
        config_data = _get_config_data(
            host_ocio_config["filepath"], formatting_data
        )
    else:
        # get config path from global
        config_global = imageio_global["ocio_config"]
        config_data = _get_config_data(
            config_global["filepath"], formatting_data
        )

    if not config_data:
        raise FileExistsError(
            "No OCIO config found in settings. It is "
            "either missing or there is typo in path inputs"
        )

    return config_data


def _get_config_data(path_list, anatomy_data):
    """Return first existing path in path list.

    If template is used in path inputs,
    then it is formatted by anatomy data
    and environment variables

    Args:
        path_list (list[str]): list of abs paths
        anatomy_data (dict): formatting data

    Returns:
        dict: config data
    """
    formatting_data = deepcopy(anatomy_data)

    # format the path for potential env vars
    formatting_data.update(dict(**os.environ))

    # first try host config paths
    for path_ in path_list:
        formatted_path = _format_path(path_, formatting_data)

        if not os.path.exists(formatted_path):
            continue

        return {
            "path": os.path.normpath(formatted_path),
            "template": path_
        }


def _format_path(template_path, formatting_data):
    """Single template path formatting.

    Args:
        template_path (str): template string
        formatting_data (dict): data to be used for
                                template formatting

    Returns:
        str: absolute formatted path
    """
    # format path for anatomy keys
    formatted_path = StringTemplate(template_path).format(
        formatting_data)

    return os.path.abspath(formatted_path)


def get_imageio_file_rules(project_name, host_name, project_settings=None):
    """Get ImageIO File rules from project settings

    Args:
        project_name (str): project name
        host_name (str): host name
        project_settings (dict, optional): project settings.
                                           Defaults to None.

    Returns:
        dict: file rules data
    """
    project_settings = project_settings or get_project_settings(project_name)

    imageio_global, imageio_host = _get_imageio_settings(
        project_settings, host_name)

    # get file rules from global and host_name
    frules_global = imageio_global["file_rules"]
    activate_global_rules = (
        frules_global.get("activate_global_file_rules", False)
        # TODO: remove this in future - backward compatibility
        or frules_global.get("enabled")
    )
    global_rules = frules_global["rules"]

    if not activate_global_rules:
        log.info(
            "Colorspace global file rules are disabled."
        )
        global_rules = {}

    # host is optional, some might not have any settings
    frules_host = imageio_host.get("file_rules", {})

    # compile file rules dictionary
    activate_host_rules = frules_host.get("activate_host_rules")
    if activate_host_rules is None:
        # TODO: remove this in future - backward compatibility
        activate_host_rules = frules_host.get("enabled", False)

    # return host rules if activated or global rules
    return frules_host["rules"] if activate_host_rules else global_rules


def get_remapped_colorspace_to_native(
    ocio_colorspace_name, host_name, imageio_host_settings
):
    """Return native colorspace name.

    Args:
        ocio_colorspace_name (str | None): ocio colorspace name
        host_name (str): Host name.
        imageio_host_settings (dict[str, Any]): ImageIO host settings.

    Returns:
        Union[str, None]: native colorspace name defined in remapping or None
    """

    CashedData.remapping.setdefault(host_name, {})
    if CashedData.remapping[host_name].get("to_native") is None:
        remapping_rules = imageio_host_settings["remapping"]["rules"]
        CashedData.remapping[host_name]["to_native"] = {
            rule["ocio_name"]: rule["host_native_name"]
            for rule in remapping_rules
        }

    return CashedData.remapping[host_name]["to_native"].get(
        ocio_colorspace_name)


def get_remapped_colorspace_from_native(
    host_native_colorspace_name, host_name, imageio_host_settings
):
    """Return ocio colorspace name remapped from host native used name.

    Args:
        host_native_colorspace_name (str): host native colorspace name
        host_name (str): Host name.
        imageio_host_settings (dict[str, Any]): ImageIO host settings.

    Returns:
        Union[str, None]: Ocio colorspace name defined in remapping or None.
    """

    CashedData.remapping.setdefault(host_name, {})
    if CashedData.remapping[host_name].get("from_native") is None:
        remapping_rules = imageio_host_settings["remapping"]["rules"]
        CashedData.remapping[host_name]["from_native"] = {
            rule["host_native_name"]: rule["ocio_name"]
            for rule in remapping_rules
        }

    return CashedData.remapping[host_name]["from_native"].get(
        host_native_colorspace_name)


def _get_imageio_settings(project_settings, host_name):
    """Get ImageIO settings for global and host

    Args:
        project_settings (dict): project settings.
                                 Defaults to None.
        host_name (str): host name

    Returns:
        tuple[dict, dict]: image io settings for global and host
    """
    # get image io from global and host_name
    imageio_global = project_settings["global"]["imageio"]
    # host is optional, some might not have any settings
    imageio_host = project_settings.get(host_name, {}).get("imageio", {})

    return imageio_global, imageio_host
