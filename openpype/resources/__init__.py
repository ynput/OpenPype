import os
from openpype import AYON_SERVER_ENABLED
from openpype.lib.openpype_version import is_running_staging

RESOURCES_DIR = os.path.dirname(os.path.abspath(__file__))


def get_resource(*args):
    """ Serves to simple resources access

    :param *args: should contain *subfolder* names and *filename* of
                  resource from resources folder
    :type *args: list
    """
    return os.path.normpath(os.path.join(RESOURCES_DIR, *args))


def get_image_path(*args):
    """Helper function to get images.

    Args:
        *<str>: Filepath part items.
    """
    return get_resource("images", *args)


def get_liberation_font_path(bold=False, italic=False):
    font_name = "LiberationSans"
    suffix = ""
    if bold:
        suffix += "Bold"
    if italic:
        suffix += "Italic"

    if not suffix:
        suffix = "Regular"

    filename = "{}-{}.ttf".format(font_name, suffix)
    font_path = get_resource("fonts", font_name, filename)
    return font_path


def get_openpype_production_icon_filepath():
    filename = "openpype_icon.png"
    if AYON_SERVER_ENABLED:
        filename = "AYON_icon.png"
    return get_resource("icons", filename)


def get_openpype_staging_icon_filepath():
    filename = "openpype_icon_staging.png"
    if AYON_SERVER_ENABLED:
        filename = "AYON_icon.png"
    return get_resource("icons", filename)


def get_openpype_icon_filepath(staging=None):
    if staging is None:
        staging = is_running_staging()

    if staging:
        return get_openpype_staging_icon_filepath()
    return get_openpype_production_icon_filepath()


def get_openpype_splash_filepath(staging=None):
    if staging is None:
        staging = is_running_staging()

    if AYON_SERVER_ENABLED:
        splash_file_name = "AYON_splash.png"
    elif staging:
        splash_file_name = "openpype_splash_staging.png"
    else:
        splash_file_name = "openpype_splash.png"
    return get_resource("icons", splash_file_name)


def pype_icon_filepath(staging=None):
    return get_openpype_icon_filepath(staging)


def pype_splash_filepath(staging=None):
    return get_openpype_splash_filepath(staging)
