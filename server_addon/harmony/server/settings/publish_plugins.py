from pydantic import Field

from ayon_server.settings import BaseSettingsModel


class CollectPalettesPlugin(BaseSettingsModel):
    """Set regular expressions to filter triggering on specific task names. '.*' means on all."""  # noqa

    allowed_tasks: list[str] = Field(
        default_factory=list,
        title="Allowed tasks"
    )


class ValidateAudioPlugin(BaseSettingsModel):
    """Check if scene contains audio track."""  #
    _isGroup = True
    enabled: bool = True
    optional: bool = Field(False, title="Optional")
    active: bool = Field(True, title="Active")


class ValidateContainersPlugin(BaseSettingsModel):
    """Check if loaded container is scene are latest versions."""
    _isGroup = True
    enabled: bool = True
    optional: bool = Field(False, title="Optional")
    active: bool = Field(True, title="Active")


class ValidateSceneSettingsPlugin(BaseSettingsModel):
    """Validate if FrameStart, FrameEnd and Resolution match shot data in DB.
       Use regular expressions to limit validations only on particular asset
       or task names."""
    _isGroup = True
    enabled: bool = True
    optional: bool = Field(False, title="Optional")
    active: bool = Field(True, title="Active")

    frame_check_filter: list[str] = Field(
        default_factory=list,
        title="Skip Frame check for Assets with name containing"
    )

    skip_resolution_check: list[str] = Field(
        default_factory=list,
        title="Skip Resolution Check for Tasks"
    )

    skip_timelines_check: list[str] = Field(
        default_factory=list,
        title="Skip Timeline Check for Tasks"
    )


class HarmonyPublishPlugins(BaseSettingsModel):

    CollectPalettes: CollectPalettesPlugin = Field(
        title="Collect Palettes",
        default_factory=CollectPalettesPlugin,
    )

    ValidateAudio: ValidateAudioPlugin = Field(
        title="Validate Audio",
        default_factory=ValidateAudioPlugin,
    )

    ValidateContainers: ValidateContainersPlugin = Field(
        title="Validate Containers",
        default_factory=ValidateContainersPlugin,
    )

    ValidateSceneSettings: ValidateSceneSettingsPlugin = Field(
        title="Validate Scene Settings",
        default_factory=ValidateSceneSettingsPlugin,
    )
