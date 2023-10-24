import os
from qtpy import QtGui

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


def get_image_path(filename):
    """Get image path from './images'.

    Returns:
        Union[str, None]: Path to image file or None if not found.
    """

    path = os.path.join(IMAGES_DIR, filename)
    if os.path.exists(path):
        return path
    return None


def get_image(filename):
    """Load image from './images' as QImage.

    Returns:
        Union[QtGui.QImage, None]: QImage or None if not found.
    """

    path = get_image_path(filename)
    if path:
        return QtGui.QImage(path)
    return None


def get_pixmap(filename):
    """Load image from './images' as QPixmap.

    Returns:
        Union[QtGui.QPixmap, None]: QPixmap or None if not found.
    """

    path = get_image_path(filename)
    if path:
        return QtGui.QPixmap(path)
    return None


def get_icon(filename):
    """Load image from './images' as QIcon.

    Returns:
        Union[QtGui.QIcon, None]: QIcon or None if not found.
    """

    pix = get_pixmap(filename)
    if pix:
        return QtGui.QIcon(pix)
    return None
