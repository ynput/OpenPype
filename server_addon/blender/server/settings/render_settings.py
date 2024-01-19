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


def renderers_enum():
    return [
        {"value": "CYCLES", "label": "Cycles"},
        {"value": "BLENDER_EEVEE", "label": "Eevee"},
    ]


def aov_list_enum():
    return [
        {"value": "empty", "label": "< none >"},
        {"value": "combined", "label": "Combined"},
        {"value": "z", "label": "Z"},
        {"value": "mist", "label": "Mist"},
        {"value": "normal", "label": "Normal"},
        {"value": "position", "label": "Position (Cycles Only)"},
        {"value": "vector", "label": "Vector (Cycles Only)"},
        {"value": "uv", "label": "UV (Cycles Only)"},
        {"value": "denoising", "label": "Denoising Data (Cycles Only)"},
        {"value": "object_index", "label": "Object Index (Cycles Only)"},
        {"value": "material_index", "label": "Material Index (Cycles Only)"},
        {"value": "sample_count", "label": "Sample Count (Cycles Only)"},
        {"value": "diffuse_light", "label": "Diffuse Light/Direct"},
        {
            "value": "diffuse_indirect",
            "label": "Diffuse Indirect (Cycles Only)"
        },
        {"value": "diffuse_color", "label": "Diffuse Color"},
        {"value": "specular_light", "label": "Specular (Glossy) Light/Direct"},
        {
            "value": "specular_indirect",
            "label": "Specular (Glossy) Indirect (Cycles Only)"
        },
        {"value": "specular_color", "label": "Specular (Glossy) Color"},
        {
            "value": "transmission_light",
            "label": "Transmission Light/Direct (Cycles Only)"
        },
        {
            "value": "transmission_indirect",
            "label": "Transmission Indirect (Cycles Only)"
        },
        {
            "value": "transmission_color",
            "label": "Transmission Color (Cycles Only)"
        },
        {"value": "volume_light", "label": "Volume Light/Direct"},
        {"value": "volume_indirect", "label": "Volume Indirect (Cycles Only)"},
        {"value": "emission", "label": "Emission"},
        {"value": "environment", "label": "Environment"},
        {"value": "shadow", "label": "Shadow/Shadow Catcher"},
        {"value": "ao", "label": "Ambient Occlusion"},
        {"value": "bloom", "label": "Bloom (Eevee Only)"},
        {"value": "transparent", "label": "Transparent (Eevee Only)"},
        {"value": "cryptomatte_object", "label": "Cryptomatte Object"},
        {"value": "cryptomatte_material", "label": "Cryptomatte Material"},
        {"value": "cryptomatte_asset", "label": "Cryptomatte Asset"},
        {
            "value": "cryptomatte_accurate",
            "label": "Cryptomatte Accurate Mode (Eevee Only)"
        },
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
    renderer: str = Field(
        "CYCLES",
        title="Renderer",
        enum_resolver=renderers_enum
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
    "renderer": "CYCLES",
    "aov_list": ["combined"],
    "custom_passes": []
}
