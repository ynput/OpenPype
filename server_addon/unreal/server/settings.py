from ayon_server.settings import BaseSettingsModel, SettingsField

from .imageio import UnrealImageIOModel


class ProjectSetup(BaseSettingsModel):
    dev_mode: bool = SettingsField(
        False,
        title="Dev mode"
    )


def _render_format_enum():
    return [
        {"value": "png", "label": "PNG"},
        {"value": "exr", "label": "EXR"},
        {"value": "jpg", "label": "JPG"},
        {"value": "bmp", "label": "BMP"}
    ]


class UnrealSettings(BaseSettingsModel):
    imageio: UnrealImageIOModel = SettingsField(
        default_factory=UnrealImageIOModel,
        title="Color Management (ImageIO)"
    )
    level_sequences_for_layouts: bool = SettingsField(
        False,
        title="Generate level sequences when loading layouts"
    )
    delete_unmatched_assets: bool = SettingsField(
        False,
        title="Delete assets that are not matched"
    )
    render_config_path: str = SettingsField(
        "",
        title="Render Config Path"
    )
    preroll_frames: int = SettingsField(
        0,
        title="Pre-roll frames"
    )
    render_format: str = SettingsField(
        "png",
        title="Render format",
        enum_resolver=_render_format_enum
    )
    project_setup: ProjectSetup = SettingsField(
        default_factory=ProjectSetup,
        title="Project Setup",
    )


DEFAULT_VALUES = {
    "level_sequences_for_layouts": True,
    "delete_unmatched_assets": False,
    "render_config_path": "",
    "preroll_frames": 0,
    "render_format": "exr",
    "project_setup": {
        "dev_mode": False
    }
}
