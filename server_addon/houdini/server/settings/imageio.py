from pydantic import Field, validator
from ayon_server.settings import BaseSettingsModel
from ayon_server.settings.validators import ensure_unique_names


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


class WorkfileImageIOModel(BaseSettingsModel):
    """Render space in Houdini is always set to 'scene_linear' Role."""

    enabled: bool = Field(False, title="Enabled")
    default_display: str = Field(title="Display")
    default_view: str = Field(title="View")
    review_color_space: str = Field(title="Review colorspace")


class HoudiniImageIOModel(BaseSettingsModel):
    activate_host_color_management: bool = Field(
        False, title="Enable Color Management"
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


DEFAULT_IMAGEIO_SETTINGS = {
    "activate_host_color_management": False,
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
        "default_display": "ACES",
        "default_view": "sRGB",
        "review_color_space": "Output - sRGB"
    }
}
