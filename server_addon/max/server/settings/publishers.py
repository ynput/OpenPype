import json
from pydantic import validator

from ayon_server.settings import BaseSettingsModel, SettingsField
from ayon_server.exceptions import BadRequestException


class ValidateAttributesModel(BaseSettingsModel):
    enabled: bool = SettingsField(title="ValidateAttributes")
    attributes: str = SettingsField(
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


class FamilyMappingItemModel(BaseSettingsModel):
    product_types: list[str] = SettingsField(
        default_factory=list,
        title="Product Types"
    )
    plugins: list[str] = SettingsField(
        default_factory=list,
        title="Plugins"
    )


class ValidateLoadedPluginModel(BaseSettingsModel):
    enabled: bool = SettingsField(title="Enabled")
    optional: bool = SettingsField(title="Optional")
    family_plugins_mapping: list[FamilyMappingItemModel] = SettingsField(
        default_factory=list,
        title="Family Plugins Mapping"
    )


class BasicValidateModel(BaseSettingsModel):
    enabled: bool = SettingsField(title="Enabled")
    optional: bool = SettingsField(title="Optional")
    active: bool = SettingsField(title="Active")


class PublishersModel(BaseSettingsModel):
    ValidateFrameRange: BasicValidateModel = SettingsField(
        default_factory=BasicValidateModel,
        title="Validate Frame Range",
        section="Validators"
    )
    ValidateAttributes: ValidateAttributesModel = SettingsField(
        default_factory=ValidateAttributesModel,
        title="Validate Attributes"
    )

    ValidateLoadedPlugin: ValidateLoadedPluginModel = SettingsField(
        default_factory=ValidateLoadedPluginModel,
        title="Validate Loaded Plugin"
    )
    ExtractModelObj: BasicValidateModel = SettingsField(
        default_factory=BasicValidateModel,
        title="Extract OBJ",
        section="Extractors"
    )
    ExtractModelFbx: BasicValidateModel = SettingsField(
        default_factory=BasicValidateModel,
        title="Extract FBX"
    )
    ExtractModelUSD: BasicValidateModel = SettingsField(
        default_factory=BasicValidateModel,
        title="Extract Geometry (USD)"
    )
    ExtractModel: BasicValidateModel = SettingsField(
        default_factory=BasicValidateModel,
        title="Extract Geometry (Alembic)"
    )
    ExtractMaxSceneRaw: BasicValidateModel = SettingsField(
        default_factory=BasicValidateModel,
        title="Extract Max Scene (Raw)"
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
    },
    "ExtractModelObj": {
        "enabled": True,
        "optional": True,
        "active": False
    },
    "ExtractModelFbx": {
        "enabled": True,
        "optional": True,
        "active": False
    },
    "ExtractModelUSD": {
        "enabled": True,
        "optional": True,
        "active": False
    },
    "ExtractModel": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ExtractMaxSceneRaw": {
        "enabled": True,
        "optional": True,
        "active": True
    }
}
