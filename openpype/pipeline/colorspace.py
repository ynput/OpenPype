import re
import os
import platform
import PyOpenColorIO as ocio
from openpype.settings import get_project_settings
from openpype.pipeline import legacy_io
from openpype.lib.log import Logger

log = Logger.get_logger(__name__)


def get_imagio_colorspace_from_filepath(
    path, host=None, project_name=None, validate=True,
    config_path=None, file_rules=None
):
    if not any([config_path, file_rules]):
        project_name = project_name or legacy_io.Session["AVALON_PROJECT"]
        host = host or legacy_io.Session["AVALON_APP"]

        config_path = get_imageio_config(project_name, host)
        file_rules = get_imageio_file_rules(project_name, host)

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
    if validate and config_path:
        config_obj = validate_imageio_config_from_path(config_path)
        validate_imageio_colorspace_in_config(config_obj, colorspace_name)

    return colorspace_name


def validate_imageio_colorspace_in_config(config_obj, colorspace_name):
    if not config_obj.getColorSpace(colorspace_name):
        raise ocio.Exception(
            "Missing colorspace '{}' in config file '{}'".format(
                colorspace_name, config_obj.getWorkingDir())
        )


def validate_imageio_config_from_path(config_path):
    try:
        config_obj = ocio.Config().CreateFromFile(config_path)
    except ocio.Exception:
        raise ocio.ExceptionMissingFile(
            "Missing ocio config file at: {}".format(config_path))

    return config_obj


def get_imageio_config(project_name, host):
    current_platform = platform.system().lower()

    imageio_global, imageio_host = _get_imageio_settings(project_name, host)

    # get config path from either global or host
    config_global = imageio_global["ocio_config"]
    config_host = imageio_host["ocio_config"]

    # set config path
    config_path = None
    if config_global["enabled"]:
        config_path = config_global["filepath"][current_platform]
    if config_host["enabled"]:
        config_path = config_host["filepath"][current_platform]

    # format the path for potential env vars
    config_path = config_path.format(**os.environ)
    return os.path.normpath(config_path)


def get_imageio_file_rules(project_name, host):

    imageio_global, imageio_host = _get_imageio_settings(project_name, host)

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


def _get_imageio_settings(project_name, host):

    # get project settings
    project_settings = get_project_settings(project_name)

    # get image io from global and host
    imageio_global = project_settings["global"]["imageio"]
    imageio_host = project_settings[host]["imageio"]

    return imageio_global, imageio_host
