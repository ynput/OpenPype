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


class ValidateCameraAttributesModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    optional: bool = Field(title="Optional")
    active: bool = Field(title="Active")
    fov: float = Field(0.0, title="Focal Length")
    nearrange: float = Field(0.0, title="Near Range")
    farrange: float = Field(0.0, title="Far Range")
    nearclip: float = Field(0.0, title="Near Clip")
    farclip: float = Field(0.0, title="Far Clip")


class FamilyMappingItemModel(BaseSettingsModel):
    product_types: list[str] = Field(
        default_factory=list,
        title="Product Types"
    )
    plugins: list[str] = Field(
        default_factory=list,
        title="Plugins"
    )


class ValidateLoadedPluginModel(BaseSettingsModel):
    enabled: bool = Field(title="Enabled")
    optional: bool = Field(title="Optional")
    family_plugins_mapping: list[FamilyMappingItemModel] = Field(
        default_factory=list,
        title="Family Plugins Mapping"
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
    ValidateCameraAttributes: ValidateCameraAttributesModel = Field(
        default_factory=ValidateCameraAttributesModel,
        title="Validate Camera Attributes",
        description=(
            "If the value of the camera attributes set to 0, "
            "the system automatically skips checking it"
        )
    )
    ValidateLoadedPlugin: ValidateLoadedPluginModel = Field(
        default_factory=ValidateLoadedPluginModel,
        title="Validate Loaded Plugin"
    )
    ExtractModelObj: BasicValidateModel = Field(
        default_factory=BasicValidateModel,
        title="Extract OBJ",
        section="Extractors"
    )
    ExtractModelFbx: BasicValidateModel = Field(
        default_factory=BasicValidateModel,
        title="Extract FBX"
    )
    ExtractModelUSD: BasicValidateModel = Field(
        default_factory=BasicValidateModel,
        title="Extract Geometry (USD)"
    )
    ExtractModel: BasicValidateModel = Field(
        default_factory=BasicValidateModel,
        title="Extract Geometry (Alembic)"
    )
    ExtractMaxSceneRaw: BasicValidateModel = Field(
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
    "ValidateCameraAttributes": {
        "enabled": True,
        "optional": True,
        "active": False,
        "fov": 45.0,
        "nearrange": 0.0,
        "farrange": 1000.0,
        "nearclip": 1.0,
        "farclip": 1000.0
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
