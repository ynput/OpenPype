import os
from Qt import QtGui

import qtawesome
from openpype.tools.utils import paint_image_with_color


class ResourceCache:
    # TODO use colors from OpenPype style
    colors = {
        "standard": "#bfccd6",
        "disabled": "#969696",
        "new": "#2d9a4c",
        "warning": "#c83232"
    }
    icons = None

    @classmethod
    def get_icon(cls, *keys):
        output = cls.get_icons()
        for key in keys:
            output = output[key]
        return output

    @classmethod
    def get_icons(cls):
        if cls.icons is None:
            cls.icons = {
                "asset": {
                    "default": qtawesome.icon(
                        "fa.folder",
                        color=cls.colors["standard"]
                    ),
                    "new": qtawesome.icon(
                        "fa.folder",
                        color=cls.colors["new"]
                    ),
                    "invalid": qtawesome.icon(
                        "fa.exclamation-triangle",
                        color=cls.colors["warning"]
                    ),
                    "removed": qtawesome.icon(
                        "fa.trash",
                        color=cls.colors["warning"]
                    )
                },
                "task": {
                    "default": qtawesome.icon(
                        "fa.check-circle-o",
                        color=cls.colors["standard"]
                    ),
                    "new": qtawesome.icon(
                        "fa.check-circle",
                        color=cls.colors["new"]
                    ),
                    "invalid": qtawesome.icon(
                        "fa.exclamation-circle",
                        color=cls.colors["warning"]
                    ),
                    "removed": qtawesome.icon(
                        "fa.trash",
                        color=cls.colors["warning"]
                    )
                },
                "refresh": qtawesome.icon(
                    "fa.refresh",
                    color=cls.colors["standard"],
                    color_disabled=cls.colors["disabled"]
                ),
                "remove": cls.get_remove_icon()
            }
        return cls.icons

    @classmethod
    def get_color(cls, color_name):
        return cls.colors[color_name]

    @classmethod
    def get_remove_icon(cls):
        src_image = get_remove_image()
        normal_pix = paint_image_with_color(
            src_image,
            QtGui.QColor(cls.colors["standard"])
        )
        disabled_pix = paint_image_with_color(
            src_image,
            QtGui.QColor(cls.colors["disabled"])
        )
        icon = QtGui.QIcon(normal_pix)
        icon.addPixmap(disabled_pix, QtGui.QIcon.Disabled, QtGui.QIcon.On)
        icon.addPixmap(disabled_pix, QtGui.QIcon.Disabled, QtGui.QIcon.Off)
        return icon


def get_remove_image():
    image_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "images",
        "bin.png"
    )
    return QtGui.QImage(image_path)
