from pydantic import Field
from ayon_server.settings import BaseSettingsModel

from .imageio import UnrealImageIOModel


class ProjectSetup(BaseSettingsModel):
    dev_mode: bool = Field(
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
    imageio: UnrealImageIOModel = Field(
        default_factory=UnrealImageIOModel,
        title="Color Management (ImageIO)"
    )
    level_sequences_for_layouts: bool = Field(
        False,
        title="Generate level sequences when loading layouts"
    )
    delete_unmatched_assets: bool = Field(
        False,
        title="Delete assets that are not matched"
    )
    render_config_path: str = Field(
        "",
        title="Render Config Path"
    )
    preroll_frames: int = Field(
        0,
        title="Pre-roll frames"
    )
    render_format: str = Field(
        "png",
        title="Render format",
        enum_resolver=_render_format_enum
    )
    project_setup: ProjectSetup = Field(
        default_factory=ProjectSetup,
        title="Project Setup",
    )


DEFAULT_VALUES = {
    "level_sequences_for_layouts": False,
    "delete_unmatched_assets": False,
    "render_config_path": "",
    "preroll_frames": 0,
    "render_format": "png",
    "project_setup": {
        "dev_mode": False
    }
}
