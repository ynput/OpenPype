import os


def get_resource(*args):
    """ Serves to simple resources access

    :param *args: should contain *subfolder* names and *filename* of
                  resource from resources folder
    :type *args: list
    """
    return os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            *args
        )
    )


def pype_icon_filepath(debug=None):
    if debug is None:
        debug = bool(os.getenv("PYPE_DEV"))

    if debug:
        icon_file_name = "pype_icon_dev.png"
    else:
        icon_file_name = "pype_icon.png"
    return get_resource("icons", icon_file_name)


def pype_splash_filepath(debug=None):
    if debug is None:
        debug = bool(os.getenv("PYPE_DEV"))

    if debug:
        splash_file_name = "pype_splash_dev.png"
    else:
        splash_file_name = "pype_splash.png"
    return get_resource("icons", splash_file_name)
