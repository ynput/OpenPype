from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    TemplateWorkfileBaseOptions,
)

from .imageio import BlenderImageIOModel
from .publish_plugins import (
    PublishPuginsModel,
    DEFAULT_BLENDER_PUBLISH_SETTINGS
)
from .render_settings import (
    RenderSettingsModel,
    DEFAULT_RENDER_SETTINGS
)


class UnitScaleSettingsModel(BaseSettingsModel):
    enabled: bool = SettingsField(True, title="Enabled")
    apply_on_opening: bool = SettingsField(
        False, title="Apply on Opening Existing Files")
    base_file_unit_scale: float = SettingsField(
        1.0, title="Base File Unit Scale"
    )


class BlenderSettings(BaseSettingsModel):
    unit_scale_settings: UnitScaleSettingsModel = SettingsField(
        default_factory=UnitScaleSettingsModel,
        title="Set Unit Scale"
    )
    set_resolution_startup: bool = SettingsField(
        True,
        title="Set Resolution on Startup"
    )
    set_frames_startup: bool = SettingsField(
        True,
        title="Set Start/End Frames and FPS on Startup"
    )
    imageio: BlenderImageIOModel = SettingsField(
        default_factory=BlenderImageIOModel,
        title="Color Management (ImageIO)"
    )
    RenderSettings: RenderSettingsModel = SettingsField(
        default_factory=RenderSettingsModel, title="Render Settings")
    workfile_builder: TemplateWorkfileBaseOptions = SettingsField(
        default_factory=TemplateWorkfileBaseOptions,
        title="Workfile Builder"
    )
    publish: PublishPuginsModel = SettingsField(
        default_factory=PublishPuginsModel,
        title="Publish Plugins"
    )


DEFAULT_VALUES = {
    "unit_scale_settings": {
        "enabled": True,
        "apply_on_opening": False,
        "base_file_unit_scale": 1.00
    },
    "set_frames_startup": True,
    "set_resolution_startup": True,
    "RenderSettings": DEFAULT_RENDER_SETTINGS,
    "publish": DEFAULT_BLENDER_PUBLISH_SETTINGS,
    "workfile_builder": {
        "create_first_version": False,
        "custom_templates": []
    }
}
