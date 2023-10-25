from pydantic import Field

from ayon_server.settings import BaseSettingsModel


class ValidateLoadedPluginModel(BaseSettingsModel):
    enabled: bool = Field(title="ValidateLoadedPlugin")
    optional: bool = Field(title="Optional")
    plugins_for_check: list[str] = Field(
        default_factory=list, title="Plugins Needed For Check"
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
        "plugins_for_check": []
    }
}
