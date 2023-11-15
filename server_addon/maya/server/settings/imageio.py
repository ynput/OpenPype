"""Providing models and setting values for image IO in Maya.

Note: Names were changed to get rid of the versions in class names.
"""
from pydantic import Field, validator

from ayon_server.settings import BaseSettingsModel, ensure_unique_names


class ImageIOConfigModel(BaseSettingsModel):
    override_global_config: bool = Field(
        False,
        title="Override global OCIO config"
    )
    filepath: list[str] = Field(
        default_factory=list,
        title="Config path"
    )


class ImageIOFileRuleModel(BaseSettingsModel):
    name: str = Field("", title="Rule name")
    pattern: str = Field("", title="Regex pattern")
    colorspace: str = Field("", title="Colorspace name")
    ext: str = Field("", title="File extension")


class ImageIOFileRulesModel(BaseSettingsModel):
    activate_host_rules: bool = Field(False)
    rules: list[ImageIOFileRuleModel] = Field(
        default_factory=list,
        title="Rules"
    )

    @validator("rules")
    def validate_unique_outputs(cls, value):
        ensure_unique_names(value)
        return value


class ColorManagementPreferenceV2Model(BaseSettingsModel):
    """Color Management Preference v2 (Maya 2022+).

    Please migrate all to 'imageio/workfile' and enable it.
    """

    enabled: bool = Field(True, title="Use Color Management Preference v2")

    renderSpace: str = Field(title="Rendering Space")
    displayName: str = Field(title="Display")
    viewName: str = Field(title="View")


class ColorManagementPreferenceModel(BaseSettingsModel):
    """Color Management Preference (legacy)."""

    renderSpace: str = Field(title="Rendering Space")
    viewTransform: str = Field(title="Viewer Transform ")


class WorkfileImageIOModel(BaseSettingsModel):
    enabled: bool = Field(True, title="Enabled")
    renderSpace: str = Field(title="Rendering Space")
    displayName: str = Field(title="Display")
    viewName: str = Field(title="View")


class ImageIOSettings(BaseSettingsModel):
    """Maya color management project settings.

    Todo: What to do with color management preferences version?
    """

    _isGroup: bool = True
    activate_host_color_management: bool = Field(
        True, title="Enable Color Management"
    )
    ocio_config: ImageIOConfigModel = Field(
        default_factory=ImageIOConfigModel,
        title="OCIO config"
    )
    file_rules: ImageIOFileRulesModel = Field(
        default_factory=ImageIOFileRulesModel,
        title="File Rules"
    )
    workfile: WorkfileImageIOModel = Field(
        default_factory=WorkfileImageIOModel,
        title="Workfile"
    )
    # Deprecated
    colorManagementPreference_v2: ColorManagementPreferenceV2Model = Field(
        default_factory=ColorManagementPreferenceV2Model,
        title="DEPRECATED: Color Management Preference v2 (Maya 2022+)"
    )
    colorManagementPreference: ColorManagementPreferenceModel = Field(
        default_factory=ColorManagementPreferenceModel,
        title="DEPRECATED: Color Management Preference (legacy)"
    )


DEFAULT_IMAGEIO_SETTINGS = {
    "activate_host_color_management": True,
    "ocio_config": {
        "override_global_config": False,
        "filepath": []
    },
    "file_rules": {
        "activate_host_rules": False,
        "rules": []
    },
    "workfile": {
        "enabled": False,
        "renderSpace": "ACES - ACEScg",
        "displayName": "ACES",
        "viewName": "sRGB"
    },
    "colorManagementPreference_v2": {
        "enabled": True,
        "renderSpace": "ACEScg",
        "displayName": "sRGB",
        "viewName": "ACES 1.0 SDR-video"
    },
    "colorManagementPreference": {
        "renderSpace": "scene-linear Rec 709/sRGB",
        "viewTransform": "sRGB gamma"
    }
}
