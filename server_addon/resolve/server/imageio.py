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


class ImageIORemappingRulesModel(BaseSettingsModel):
    host_native_name: str = Field(
        title="Application native colorspace name"
    )
    ocio_name: str = Field(title="OCIO colorspace name")


class ImageIORemappingModel(BaseSettingsModel):
    rules: list[ImageIORemappingRulesModel] = Field(
        default_factory=list)


class ResolveImageIOModel(BaseSettingsModel):
    activate_host_color_management: bool = Field(
        True, title="Enable Color Management"
    )
    remapping: ImageIORemappingModel = Field(
        title="Remapping colorspace names",
        default_factory=ImageIORemappingModel
    )
    ocio_config: ImageIOConfigModel = Field(
        default_factory=ImageIOConfigModel,
        title="OCIO config"
    )
    file_rules: ImageIOFileRulesModel = Field(
        default_factory=ImageIOFileRulesModel,
        title="File Rules"
    )
