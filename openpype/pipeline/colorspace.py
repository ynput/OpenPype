from copy import deepcopy
import re
import os
import sys
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


def get_data_subprocess(config_path, data_type):
    """Get data via subprocess

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


def compatible_python():
    """Only 3.9 or higher can directly use PyOpenColorIO in ocio_wrapper"""
    compatible = False
    if sys.version[0] == 3 and sys.version[1] >= 9:
        compatible = True
    return compatible


def get_ocio_config_colorspaces(config_path):
    """Get all colorspace data

    Wrapper function for aggregating all names and its families.
    Families can be used for building menu and submenus in gui.

    Args:
        config_path (str): path leading to config.ocio file

    Returns:
        dict: colorspace and family in couple
    """
    if compatible_python():
        from ..scripts.ocio_wrapper import _get_colorspace_data
        return _get_colorspace_data(config_path)
    else:
        return get_colorspace_data_subprocess(config_path)


def get_colorspace_data_subprocess(config_path):
    """Get colorspace data via subprocess

    Wrapper for Python 2 hosts.

    Args:
        config_path (str): path leading to config.ocio file

    Returns:
        dict: colorspace and family in couple
    """
    return get_data_subprocess(config_path, "get_colorspace")


def get_ocio_config_views(config_path):
    """Get all viewer data

    Wrapper function for aggregating all display and related viewers.
    Key can be used for building gui menu with submenus.

    Args:
        config_path (str): path leading to config.ocio file

    Returns:
        dict: `display/viewer` and viewer data
    """
    if compatible_python():
        from ..scripts.ocio_wrapper import _get_views_data
        return _get_views_data(config_path)
    else:
        return get_views_data_subprocess(config_path)


def get_views_data_subprocess(config_path):
    """Get viewers data via subprocess

    Wrapper for Python 2 hosts.

    Args:
        config_path (str): path leading to config.ocio file

    Returns:
        dict: `display/viewer` and viewer data
    """
    return get_data_subprocess(config_path, "get_views")


def get_imageio_config(
    project_name, host_name,
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
        project_settings (dict, optional): project settings.
                                           Defaults to None.
        anatomy_data (dict, optional): anatomy formatting data.
                                       Defaults to None.
        anatomy (lib.Anatomy, optional): Anatomy object.
                                         Defaults to None.

    Returns:
        dict or bool: config path data or None
    """
    project_settings = project_settings or get_project_settings(project_name)
    anatomy = anatomy or Anatomy(project_name)

    if not anatomy_data:
        from openpype.pipeline.context_tools import (
            get_template_data_from_session)
        anatomy_data = get_template_data_from_session()

    formatting_data = deepcopy(anatomy_data)
    # add project roots to anatomy data
    formatting_data["root"] = anatomy.roots
    formatting_data["platform"] = platform.system().lower()

    # get colorspace settings
    imageio_global, imageio_host = _get_imageio_settings(
        project_settings, host_name)

    config_host = imageio_host.get("ocio_config", {})

    if config_host.get("enabled"):
        config_data = _get_config_data(
            config_host["filepath"], formatting_data
        )
    else:
        config_data = None

    if not config_data:
        # get config path from either global or host_name
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
    # host is optional, some might not have any settings
    frules_host = imageio_host.get("file_rules", {})

    # compile file rules dictionary
    file_rules = {}
    if frules_global["enabled"]:
        file_rules.update(frules_global["rules"])
    if frules_host and frules_host["enabled"]:
        file_rules.update(frules_host["rules"])

    return file_rules


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
