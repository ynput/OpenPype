import json
from pydantic import Field, validator
from ayon_server.exceptions import BadRequestException
from ayon_server.settings import BaseSettingsModel


def validate_json_dict(value):
    if not value.strip():
        return "{}"
    try:
        converted_value = json.loads(value)
        success = isinstance(converted_value, dict)
    except json.JSONDecodeError:
        success = False

    if not success:
        raise BadRequestException(
            "Environment's can't be parsed as json object"
        )
    return value


class ValidatePluginModel(BaseSettingsModel):
    enabled: bool = Field(True)
    optional: bool = Field(title="Optional")
    active: bool = Field(title="Active")


class ExtractBlendModel(BaseSettingsModel):
    enabled: bool = Field(True)
    optional: bool = Field(title="Optional")
    active: bool = Field(title="Active")
    families: list[str] = Field(
        default_factory=list,
        title="Families"
    )


class ExtractPlayblastModel(BaseSettingsModel):
    enabled: bool = Field(True)
    optional: bool = Field(title="Optional")
    active: bool = Field(title="Active")
    presets: str = Field("", title="Presets", widget="textarea")

    @validator("presets")
    def validate_json(cls, value):
        return validate_json_dict(value)


class PublishPuginsModel(BaseSettingsModel):
    ValidateCameraZeroKeyframe: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Validate Camera Zero Keyframe",
        section="Validators"
    )
    ValidateMeshHasUvs: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Validate Mesh Has Uvs"
    )
    ValidateMeshNoNegativeScale: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Validate Mesh No Negative Scale"
    )
    ValidateTransformZero: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Validate Transform Zero"
    )
    ValidateNoColonsInName: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Validate No Colons In Name"
    )
    ExtractBlend: ExtractBlendModel = Field(
        default_factory=ExtractBlendModel,
        title="Extract Blend",
        section="Extractors"
    )
    ExtractFBX: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Extract FBX"
    )
    ExtractABC: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Extract ABC"
    )
    ExtractBlendAnimation: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Extract Blend Animation"
    )
    ExtractAnimationFBX: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Extract Animation FBX"
    )
    ExtractCamera: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Extract Camera"
    )
    ExtractLayout: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Extract Layout"
    )
    ExtractThumbnail: ExtractPlayblastModel = Field(
        default_factory=ExtractPlayblastModel,
        title="Extract Thumbnail"
    )
    ExtractPlayblast: ExtractPlayblastModel = Field(
        default_factory=ExtractPlayblastModel,
        title="Extract Playblast"
    )


DEFAULT_BLENDER_PUBLISH_SETTINGS = {
    "ValidateCameraZeroKeyframe": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateMeshHasUvs": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ValidateMeshNoNegativeScale": {
        "enabled": True,
        "optional": False,
        "active": True
    },
    "ValidateTransformZero": {
        "enabled": True,
        "optional": False,
        "active": True
    },
    "ValidateNoColonsInName": {
        "enabled": True,
        "optional": False,
        "active": True
    },
    "ExtractBlend": {
        "enabled": True,
        "optional": True,
        "active": True,
        "families": [
            "model",
            "camera",
            "rig",
            "action",
            "layout"
        ]
    },
    "ExtractFBX": {
        "enabled": True,
        "optional": True,
        "active": False
    },
    "ExtractABC": {
        "enabled": True,
        "optional": True,
        "active": False
    },
    "ExtractBlendAnimation": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ExtractAnimationFBX": {
        "enabled": True,
        "optional": True,
        "active": False
    },
    "ExtractCamera": {
        "enabled": True,
        "optional": True,
        "active": True
    },
    "ExtractLayout": {
        "enabled": True,
        "optional": True,
        "active": False
    },
    "ExtractThumbnail": {
        "enabled": True,
        "optional": True,
        "active": True,
        "presets": "{\n    \"model\": {\n        \"image_settings\": {\n            \"file_format\": \"JPEG\",\n            \"color_mode\": \"RGB\",\n            \"quality\": 100\n        },\n        \"display_options\": {\n            \"shading\": {\n                \"light\": \"STUDIO\",\n                \"studio_light\": \"Default\",\n                \"type\": \"SOLID\",\n                \"color_type\": \"OBJECT\",\n                \"show_xray\": false,\n                \"show_shadows\": false,\n                \"show_cavity\": true\n            },\n            \"overlay\": {\n                \"show_overlays\": false\n            }\n        }\n    },\n    \"rig\": {\n        \"image_settings\": {\n            \"file_format\": \"JPEG\",\n            \"color_mode\": \"RGB\",\n            \"quality\": 100\n        },\n        \"display_options\": {\n            \"shading\": {\n                \"light\": \"STUDIO\",\n                \"studio_light\": \"Default\",\n                \"type\": \"SOLID\",\n                \"color_type\": \"OBJECT\",\n                \"show_xray\": true,\n                \"show_shadows\": false,\n                \"show_cavity\": false\n            },\n            \"overlay\": {\n                \"show_overlays\": true,\n                \"show_ortho_grid\": false,\n                \"show_floor\": false,\n                \"show_axis_x\": false,\n                \"show_axis_y\": false,\n                \"show_axis_z\": false,\n                \"show_text\": false,\n                \"show_stats\": false,\n                \"show_cursor\": false,\n                \"show_annotation\": false,\n                \"show_extras\": false,\n                \"show_relationship_lines\": false,\n                \"show_outline_selected\": false,\n                \"show_motion_paths\": false,\n                \"show_object_origins\": false,\n                \"show_bones\": true\n            }\n        }\n    }\n}"
    },
    "ExtractPlayblast": {
        "enabled": True,
        "optional": True,
        "active": True,
        "presets": "{\n    \"default\": {\n        \"image_settings\": {\n            \"file_format\": \"PNG\",\n            \"color_mode\": \"RGB\",\n            \"color_depth\": \"8\",\n            \"compression\": 15\n        },\n        \"display_options\": {\n            \"shading\": {\n                \"type\": \"MATERIAL\",\n                \"render_pass\": \"COMBINED\"\n            },\n            \"overlay\": {\n                \"show_overlays\": false\n            }\n        }\n    }\n}"
    }
}
