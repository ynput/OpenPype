from pydantic import Field

from ayon_server.settings import BaseSettingsModel


class FamilyPluginsMappingModel(BaseSettingsModel):
    _layout = "compact"
    families: str = Field(title="Families")
    plugins: str = Field(title="Plugins")


class ValidateLoadedPluginModel(BaseSettingsModel):
    enabled: bool = Field(title="ValidateLoadedPlugin")
    optional: bool = Field(title="Optional")
    family_plugins_mapping: list[FamilyPluginsMappingModel] = Field(
        default_factory=list, title="Family Plugins Mapping"
    )


class BasicValidateModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    optional: bool = Field(title="Optional")
    active: bool = Field(title="Active")


class PublishersModel(BaseSettingsModel):
    ValidateFrameRange: BasicValidateModel = Field(
        default_factory=BasicValidateModel,
        title="Validate Frame Range",
        section="Validators"
    )
    ValidateLoadedPlugin: ValidateLoadedPluginModel = Field(
        default_factory=ValidateLoadedPluginModel,
        title="Validate Loaded Plugin"
    )

DEFAULT_PUBLISH_SETTINGS = {
    "ValidateFrameRange": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateLoadedPlugin": {
        "enabled": False,
        "optional": True,
        "family_plugins_mapping": {}
    }
}
