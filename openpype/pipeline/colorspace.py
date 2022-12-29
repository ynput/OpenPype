import re
import os
import platform
import PyOpenColorIO as ocio
from openpype.settings import get_project_settings
from openpype.lib import StringTemplate
from openpype.pipeline import Anatomy
from openpype.pipeline.template_data import get_template_data_with_names
from openpype.lib.log import Logger

log = Logger.get_logger(__name__)


def get_imagio_colorspace_from_filepath(
    path, host, project_name,
    config_data=None, file_rules=None,
    project_settings=None,
    validate=True
):
    if not any([config_data, file_rules]):
        project_settings = project_settings or get_project_settings(
            project_name
        )
        config_data = get_imageio_config(
            project_name, host, project_settings)
        file_rules = get_imageio_file_rules(
            project_name, host, project_settings)

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
        validate_imageio_config_from_path(
            config_data["path"])
        validate_imageio_colorspace_in_config(
            config_data["path"], colorspace_name)

    return colorspace_name


def validate_imageio_colorspace_in_config(config_path, colorspace_name):
    config_obj = get_ocio_config(config_path)
    if not config_obj.getColorSpace(colorspace_name):
        raise ocio.Exception(
            "Missing colorspace '{}' in config file '{}'".format(
                colorspace_name, config_obj.getWorkingDir())
        )


def validate_imageio_config_from_path(config_path):
    try:
        config_obj = get_ocio_config(config_path)
    except ocio.Exception:
        raise ocio.ExceptionMissingFile(
            "Missing ocio config file at: {}".format(config_path))

    return config_obj


def get_ocio_config(config_path):
    return ocio.Config().CreateFromFile(config_path)


def get_imageio_config(
    project_name, host_name,
    project_settings=None,
    anatomy_formating_data=None,
    anatomy=None
):
    project_settings = project_settings or get_project_settings(project_name)
    anatomy = anatomy or Anatomy(project_name)
    current_platform = platform.system().lower()

    # get anatomy data for formating path template
    anatomy_data = anatomy_formating_data or get_template_data_with_names(
        project_name
    )
    # add project roots to anatomy data
    anatomy_data["root"] = anatomy.roots

    # get colorspace settings
    imageio_global, imageio_host = _get_imageio_settings(
        project_settings, host_name)

    # get config path from either global or host
    config_global = imageio_global["ocio_config"]
    config_host = imageio_host["ocio_config"]

    # set config path
    config_path = None
    if config_global["enabled"]:
        config_path = config_global["filepath"][current_platform]
    if config_host["enabled"]:
        config_path = config_host["filepath"][current_platform]

    if not config_path:
        return

    # format the path for potential env vars
    formated_path = config_path.format(**os.environ)

    # format path for anatomy keys
    formated_path = StringTemplate(formated_path).format(
        anatomy_data)

    abs_path = os.path.abspath(formated_path)
    return {
        "path": os.path.normpath(abs_path),
        "template": config_path
    }


def get_imageio_file_rules(project_name, host_name, project_settings=None):

    project_settings = project_settings or get_project_settings(project_name)

    imageio_global, imageio_host = _get_imageio_settings(
        project_settings, host_name)

    # get file rules from global and host
    frules_global = imageio_global["file_rules"]
    frules_host = imageio_host["file_rules"]

    # compile file rules dictionary
    file_rules = {}
    if frules_global["enabled"]:
        file_rules.update(frules_global["rules"])
    if frules_host["enabled"]:
        file_rules.update(frules_host["rules"])

    return file_rules


def _get_imageio_settings(project_settings, host_name):

    # get image io from global and host
    imageio_global = project_settings["global"]["imageio"]
    imageio_host = project_settings[host_name]["imageio"]

    return imageio_global, imageio_host
