import os

from Qt import QtGui


def get_icon_path(icon_name=None, filename=None):
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


def get_pixmap(icon_name=None, filename=None):
    path = get_icon_path(icon_name, filename)
    if not path:
        return None

    return QtGui.QPixmap(path)


def get_icon(icon_name=None, filename=None):
    pix = get_pixmap(icon_name, filename)
    if not pix:
        return None
    return QtGui.QIcon(pix)
