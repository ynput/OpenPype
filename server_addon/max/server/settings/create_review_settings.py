from ayon_server.settings import BaseSettingsModel, SettingsField


def image_format_enum():
    """Return enumerator for image output formats."""
    return [
        {"label": "exr", "value": "exr"},
        {"label": "jpg", "value": "jpg"},
        {"label": "png", "value": "png"},
        {"label": "tga", "value": "tga"}
    ]


def visual_style_enum():
    """Return enumerator for viewport visual style."""
    return [
        {"label": "Realistic", "value": "Realistic"},
        {"label": "Shaded", "value": "Shaded"},
        {"label": "Facets", "value": "Facets"},
        {"label": "ConsistentColors",
         "value": "ConsistentColors"},
        {"label": "Wireframe", "value": "Wireframe"},
        {"label": "BoundingBox", "value": "BoundingBox"},
        {"label": "Ink", "value": "Ink"},
        {"label": "ColorInk", "value": "ColorInk"},
        {"label": "Acrylic", "value": "Acrylic"},
        {"label": "Tech", "value": "Tech"},
        {"label": "Graphite", "value": "Graphite"},
        {"label": "ColorPencil", "value": "ColorPencil"},
        {"label": "Pastel", "value": "Pastel"},
        {"label": "Clay", "value": "Clay"},
        {"label": "ModelAssist", "value": "ModelAssist"}
    ]


def preview_preset_enum():
    """Return enumerator for viewport visual preset."""
    return [
        {"label": "Quality", "value": "Quality"},
        {"label": "Standard", "value": "Standard"},
        {"label": "Performance", "value": "Performance"},
        {"label": "DXMode", "value": "DXMode"},
        {"label": "Customize", "value": "Customize"},
    ]


def anti_aliasing_enum():
    """Return enumerator for viewport anti-aliasing."""
    return [
        {"label": "None", "value": "None"},
        {"label": "2X", "value": "2X"},
        {"label": "4X", "value": "4X"},
        {"label": "8X", "value": "8X"}
    ]


class CreateReviewModel(BaseSettingsModel):
    review_width: int = SettingsField(1920, title="Review Width")
    review_height: int = SettingsField(1080, title="Review Height")
    percentSize: float = SettingsField(100.0, title="Percent of Output")
    keep_images: bool = SettingsField(False, title="Keep Image Sequences")
    image_format: str = SettingsField(
        enum_resolver=image_format_enum,
        title="Image Format Options"
    )
    visual_style: str = SettingsField(
        enum_resolver=visual_style_enum,
        title="Preference"
    )
    viewport_preset: str = SettingsField(
        enum_resolver=preview_preset_enum,
        title="Preview Preset"
    )
    anti_aliasing: str = SettingsField(
        enum_resolver=anti_aliasing_enum,
        title="Anti-aliasing Quality"
    )
    vp_texture: bool = SettingsField(True, title="Viewport Texture")


DEFAULT_CREATE_REVIEW_SETTINGS = {
    "review_width": 1920,
    "review_height": 1080,
    "percentSize": 100.0,
    "keep_images": False,
    "image_format": "png",
    "visual_style": "Realistic",
    "viewport_preset": "Quality",
    "anti_aliasing": "None",
    "vp_texture": True
}
