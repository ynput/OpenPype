from ayon_server.settings import BaseSettingsModel, SettingsField


def aov_separators_enum():
    return [
        {"value": "dash", "label": "- (dash)"},
        {"value": "underscore", "label": "_ (underscore)"},
        {"value": "dot", "label": ". (dot)"}
    ]


def image_format_enum():
    """Return enumerator for image output formats."""
    return [
        {"label": "bmp", "value": "bmp"},
        {"label": "exr", "value": "exr"},
        {"label": "tif", "value": "tif"},
        {"label": "tiff", "value": "tiff"},
        {"label": "jpg", "value": "jpg"},
        {"label": "png", "value": "png"},
        {"label": "tga", "value": "tga"},
        {"label": "dds", "value": "dds"}
    ]


class RenderSettingsModel(BaseSettingsModel):
    default_render_image_folder: str = SettingsField(
        title="Default render image folder"
    )
    aov_separator: str = SettingsField(
        "underscore",
        title="AOV Separator character",
        enum_resolver=aov_separators_enum
    )
    image_format: str = SettingsField(
        enum_resolver=image_format_enum,
        title="Output Image Format"
    )
    multipass: bool = SettingsField(title="multipass")


DEFAULT_RENDER_SETTINGS = {
    "default_render_image_folder": "renders/3dsmax",
    "aov_separator": "underscore",
    "image_format": "exr",
    "multipass": True
}
