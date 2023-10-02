"""Providing models and values for Blender Render Settings."""
from pydantic import Field

from ayon_server.settings import BaseSettingsModel


def aov_separators_enum():
    return [
        {"value": "dash", "label": "- (dash)"},
        {"value": "underscore", "label": "_ (underscore)"},
        {"value": "dot", "label": ". (dot)"}
    ]


def image_format_enum():
    return [
        {"value": "exr", "label": "OpenEXR"},
        {"value": "bmp", "label": "BMP"},
        {"value": "rgb", "label": "Iris"},
        {"value": "png", "label": "PNG"},
        {"value": "jpg", "label": "JPEG"},
        {"value": "jp2", "label": "JPEG 2000"},
        {"value": "tga", "label": "Targa"},
        {"value": "tif", "label": "TIFF"},
    ]


def aov_list_enum():
    return [
        {"value": "empty", "label": "< none >"},
        {"value": "combined", "label": "Combined"},
        {"value": "z", "label": "Z"},
        {"value": "mist", "label": "Mist"},
        {"value": "normal", "label": "Normal"},
        {"value": "diffuse_light", "label": "Diffuse Light"},
        {"value": "diffuse_color", "label": "Diffuse Color"},
        {"value": "specular_light", "label": "Specular Light"},
        {"value": "specular_color", "label": "Specular Color"},
        {"value": "volume_light", "label": "Volume Light"},
        {"value": "emission", "label": "Emission"},
        {"value": "environment", "label": "Environment"},
        {"value": "shadow", "label": "Shadow"},
        {"value": "ao", "label": "Ambient Occlusion"},
        {"value": "denoising", "label": "Denoising"},
        {"value": "volume_direct", "label": "Direct Volumetric Scattering"},
        {"value": "volume_indirect", "label": "Indirect Volumetric Scattering"}
    ]


def custom_passes_types_enum():
    return [
        {"value": "COLOR", "label": "Color"},
        {"value": "VALUE", "label": "Value"},
    ]


class CustomPassesModel(BaseSettingsModel):
    """Custom Passes"""
    _layout = "compact"

    attribute: str = Field("", title="Attribute name")
    value: str = Field(
        "COLOR",
        title="Type",
        enum_resolver=custom_passes_types_enum
    )


class RenderSettingsModel(BaseSettingsModel):
    default_render_image_folder: str = Field(
        title="Default Render Image Folder"
    )
    aov_separator: str = Field(
        "underscore",
        title="AOV Separator Character",
        enum_resolver=aov_separators_enum
    )
    image_format: str = Field(
        "exr",
        title="Image Format",
        enum_resolver=image_format_enum
    )
    multilayer_exr: bool = Field(
        title="Multilayer (EXR)"
    )
    aov_list: list[str] = Field(
        default_factory=list,
        enum_resolver=aov_list_enum,
        title="AOVs to create"
    )
    custom_passes: list[CustomPassesModel] = Field(
        default_factory=list,
        title="Custom Passes",
        description=(
            "Add custom AOVs. They are added to the view layer and in the "
            "Compositing Nodetree,\nbut they need to be added manually to "
            "the Shader Nodetree."
        )
    )


DEFAULT_RENDER_SETTINGS = {
    "default_render_image_folder": "renders/blender",
    "aov_separator": "underscore",
    "image_format": "exr",
    "multilayer_exr": True,
    "aov_list": [],
    "custom_passes": []
}
