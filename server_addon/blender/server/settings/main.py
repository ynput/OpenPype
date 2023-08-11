from pydantic import Field
from ayon_server.settings import (
    BaseSettingsModel,
    TemplateWorkfileBaseOptions,
)

from .imageio import BlenderImageIOModel
from .publish_plugins import (
    PublishPuginsModel,
    DEFAULT_BLENDER_PUBLISH_SETTINGS
)


class UnitScaleSettingsModel(BaseSettingsModel):
    enabled: bool = Field(True, title="Enabled")
    apply_on_opening: bool = Field(
        False, title="Apply on Opening Existing Files")
    base_file_unit_scale: float = Field(
        1.0, title="Base File Unit Scale"
    )


class BlenderSettings(BaseSettingsModel):
    unit_scale_settings: UnitScaleSettingsModel = Field(
        default_factory=UnitScaleSettingsModel,
        title="Set Unit Scale"
    )
    set_resolution_startup: bool = Field(
        True,
        title="Set Resolution on Startup"
    )
    set_frames_startup: bool = Field(
        True,
        title="Set Start/End Frames and FPS on Startup"
    )
    imageio: BlenderImageIOModel = Field(
        default_factory=BlenderImageIOModel,
        title="Color Management (ImageIO)"
    )
    workfile_builder: TemplateWorkfileBaseOptions = Field(
        default_factory=TemplateWorkfileBaseOptions,
        title="Workfile Builder"
    )
    publish: PublishPuginsModel = Field(
        default_factory=PublishPuginsModel,
        title="Publish Plugins"
    )


DEFAULT_VALUES = {
    "unit_scale_settings": {
        "enabled": True,
        "apply_on_opening": False,
        "base_file_unit_scale": 0.01
    },
    "set_frames_startup": True,
    "set_resolution_startup": True,
    "publish": DEFAULT_BLENDER_PUBLISH_SETTINGS,
    "workfile_builder": {
        "create_first_version": False,
        "custom_templates": []
    }
}
