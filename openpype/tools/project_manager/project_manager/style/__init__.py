import os
from openpype import resources
from avalon.vendor import qtawesome


class ResourceCache:
    colors = {
        "standard": "#333333",
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
                    color=cls.colors["standard"]
                )
            }
        return cls.icons

    @classmethod
    def get_color(cls, color_name):
        return cls.colors[color_name]

    @classmethod
    def style_fill_data(cls):
        output = {}
        for color_name, color_value in cls.colors.items():
            key = "color:{}".format(color_name)
            output[key] = color_value
        return output


def load_stylesheet():
    from . import qrc_resources

    qrc_resources.qInitResources()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    style_path = os.path.join(current_dir, "style.css")
    with open(style_path, "r") as style_file:
        stylesheet = style_file.read()

    for key, value in ResourceCache.style_fill_data().items():
        replacement_key = "{" + key + "}"
        stylesheet = stylesheet.replace(replacement_key, value)
    return stylesheet


def app_icon_path():
    return resources.pype_icon_filepath()
