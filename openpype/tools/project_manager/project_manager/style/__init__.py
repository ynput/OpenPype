import os
from openpype import resources
from avalon.vendor import qtawesome


class ResourceCache:
    colors = {
        "standard": "#333333",
        "warning": "#ff0000",
        "new": "#00ff00"
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
                    "existing": qtawesome.icon(
                        "fa.folder",
                        color=cls.colors["standard"]
                    ),
                    "new": qtawesome.icon(
                        "fa.folder",
                        color=cls.colors["new"]
                    ),
                    "duplicated": qtawesome.icon(
                        "fa.folder",
                        color=cls.colors["warning"]
                    ),
                    "removed": qtawesome.icon(
                        "fa.trash",
                        color=cls.colors["warning"]
                    )
                },
                "task": {
                    "existing": qtawesome.icon(
                        "fa.check-circle-o",
                        color=cls.colors["standard"]
                    ),
                    "new": qtawesome.icon(
                        "fa.check-circle",
                        color=cls.colors["new"]
                    ),
                    "duplicated": qtawesome.icon(
                        "fa.check-circle",
                        color=cls.colors["warning"]
                    ),
                    "removed": qtawesome.icon(
                        "fa.trash",
                        color=cls.colors["warning"]
                    )
                },
                "refresh": qtawesome.icon(
                    "fa.refresh",
                    color=cls.colors["standard"]
                )
            }
        return cls.icons

    @classmethod
    def get_color(cls, color_name):
        return cls.colors[color_name]


def load_stylesheet():
    style_path = os.path.join(os.path.dirname(__file__), "style.css")
    with open(style_path, "r") as style_file:
        stylesheet = style_file.read()
    return stylesheet


def app_icon_path():
    return resources.pype_icon_filepath()
