import json
from pydantic import Field, validator

from ayon_server.settings import BaseSettingsModel
from ayon_server.exceptions import BadRequestException


class ValidateAttributesModel(BaseSettingsModel):
    enabled: bool = Field(title="ValidateAttributes")
    attributes: str = Field(
        "{}", title="Attributes", widget="textarea")

    @validator("attributes")
    def validate_json(cls, value):
        if not value.strip():
            return "{}"
        try:
            converted_value = json.loads(value)
            success = isinstance(converted_value, dict)
        except json.JSONDecodeError:
            success = False

        if not success:
            raise BadRequestException(
                "The attibutes can't be parsed as json object"
            )
        return value


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
    ValidateAttributes: ValidateAttributesModel = Field(
        default_factory=ValidateAttributesModel,
        title="Validate Attributes"
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
    "ValidateAttributes": {
        "enabled": False,
        "attributes": "{}"
    },
    "ValidateLoadedPlugin": {
        "enabled": False,
        "optional": True,
        "family_plugins_mapping": []
    }
}
