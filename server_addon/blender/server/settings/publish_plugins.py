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


class ValidateFileSavedModel(BaseSettingsModel):
    enabled: bool = Field(title="ValidateFileSaved")
    optional: bool = Field(title="Optional")
    active: bool = Field(title="Active")
    exclude_families: list[str] = Field(
        default_factory=list,
        title="Exclude product types"
    )


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
    ValidateFileSaved: ValidateFileSavedModel = Field(
        default_factory=ValidateFileSavedModel,
        title="Validate File Saved",
        section="Validators"
    )
    ValidateRenderCameraIsSet: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Validate Render Camera Is Set",
        section="Validators"
    )
    ValidateDeadlinePublish: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Validate Render Output for Deadline",
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
    ExtractCameraABC: ValidatePluginModel = Field(
        default_factory=ValidatePluginModel,
        title="Extract Camera as ABC"
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
    "ValidateFileSaved": {
        "enabled": True,
        "optional": False,
        "active": True,
        "exclude_families": []
    },
    "ValidateRenderCameraIsSet": {
        "enabled": True,
        "optional": False,
        "active": True
    },
    "ValidateDeadlinePublish": {
        "enabled": True,
        "optional": False,
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
            "layout",
            "blendScene"
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
    "ExtractCameraABC": {
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
        "presets": json.dumps(
            {
                "model": {
                    "image_settings": {
                        "file_format": "JPEG",
                        "color_mode": "RGB",
                        "quality": 100
                    },
                    "display_options": {
                        "shading": {
                            "light": "STUDIO",
                            "studio_light": "Default",
                            "type": "SOLID",
                            "color_type": "OBJECT",
                            "show_xray": False,
                            "show_shadows": False,
                            "show_cavity": True
                        },
                        "overlay": {
                            "show_overlays": False
                        }
                    }
                },
                "rig": {
                    "image_settings": {
                        "file_format": "JPEG",
                        "color_mode": "RGB",
                        "quality": 100
                    },
                    "display_options": {
                        "shading": {
                            "light": "STUDIO",
                            "studio_light": "Default",
                            "type": "SOLID",
                            "color_type": "OBJECT",
                            "show_xray": True,
                            "show_shadows": False,
                            "show_cavity": False
                        },
                        "overlay": {
                            "show_overlays": True,
                            "show_ortho_grid": False,
                            "show_floor": False,
                            "show_axis_x": False,
                            "show_axis_y": False,
                            "show_axis_z": False,
                            "show_text": False,
                            "show_stats": False,
                            "show_cursor": False,
                            "show_annotation": False,
                            "show_extras": False,
                            "show_relationship_lines": False,
                            "show_outline_selected": False,
                            "show_motion_paths": False,
                            "show_object_origins": False,
                            "show_bones": True
                        }
                    }
                }
            },
            indent=4,
        )
    },
    "ExtractPlayblast": {
        "enabled": True,
        "optional": True,
        "active": True,
        "presets": json.dumps(
            {
                "default": {
                    "image_settings": {
                        "file_format": "PNG",
                        "color_mode": "RGB",
                        "color_depth": "8",
                        "compression": 15
                    },
                    "display_options": {
                        "shading": {
                            "type": "MATERIAL",
                            "render_pass": "COMBINED"
                        },
                        "overlay": {
                            "show_overlays": False
                        }
                    }
                }
            },
            indent=4
        )
    }
}
