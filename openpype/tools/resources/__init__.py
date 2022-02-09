import os

from Qt import QtGui


def get_icon_path(icon_name=None, filename=None):
    """Path to image in './images' folder."""
    if icon_name is None and filename is None:
        return None

    if filename is None:
        filename = "{}.png".format(icon_name)

    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "images",
        filename
    )
    if os.path.exists(path):
        return path
    return None


def get_image(icon_name=None, filename=None):
    """Load image from './images' as QImage."""
    path = get_icon_path(icon_name, filename)
    if path:
        return QtGui.QImage(path)
    return None


def get_pixmap(icon_name=None, filename=None):
    """Load image from './images' as QPixmap."""
    path = get_icon_path(icon_name, filename)
    if path:
        return QtGui.QPixmap(path)
    return None


def get_icon(icon_name=None, filename=None):
    """Load image from './images' as QICon."""
    pix = get_pixmap(icon_name, filename)
    if pix:
        return QtGui.QIcon(pix)
    return None
