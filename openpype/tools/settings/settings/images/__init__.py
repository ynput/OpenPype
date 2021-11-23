import os
from Qt import QtGui


def get_image_path(image_filename):
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        image_filename
    )


def get_image(image_filename):
    image_path = get_image_path(image_filename)
    return QtGui.QImage(image_path)


def get_pixmap(image_filename):
    image_path = get_image_path(image_filename)
    return QtGui.QPixmap(image_path)
