from pydantic import validator
from ayon_server.settings import (
    BaseSettingsModel,
    SettingsField,
    ensure_unique_names
)
from .common import KnobModel


def instance_attributes_enum():
    """Return create write instance attributes."""
    return [
        {"value": "reviewable", "label": "Reviewable"},
        {"value": "farm_rendering", "label": "Farm rendering"},
        {"value": "use_range_limit", "label": "Use range limit"}
    ]


class PrenodeModel(BaseSettingsModel):
    name: str = SettingsField(
        title="Node name"
    )

    nodeclass: str = SettingsField(
        "",
        title="Node class"
    )
    dependent: str = SettingsField(
        "",
        title="Incoming dependency"
    )

    knobs: list[KnobModel] = SettingsField(
        default_factory=list,
        title="Knobs",
    )

    @validator("knobs")
    def ensure_unique_names(cls, value):
        """Ensure name fields within the lists have unique names."""
        ensure_unique_names(value)
        return value


class CreateWriteRenderModel(BaseSettingsModel):
    temp_rendering_path_template: str = SettingsField(
        title="Temporary rendering path template"
    )
    default_variants: list[str] = SettingsField(
        title="Default variants",
        default_factory=list
    )
    instance_attributes: list[str] = SettingsField(
        default_factory=list,
        enum_resolver=instance_attributes_enum,
        title="Instance attributes"
    )
    exposed_knobs: list[str] = SettingsField(
        title="Write Node Exposed Knobs",
        default_factory=list
    )
    prenodes: list[PrenodeModel] = SettingsField(
        default_factory=list,
        title="Preceding nodes",
    )

    @validator("prenodes")
    def ensure_unique_names(cls, value):
        """Ensure name fields within the lists have unique names."""
        ensure_unique_names(value)
        return value


class CreateWritePrerenderModel(BaseSettingsModel):
    temp_rendering_path_template: str = SettingsField(
        title="Temporary rendering path template"
    )
    default_variants: list[str] = SettingsField(
        title="Default variants",
        default_factory=list
    )
    instance_attributes: list[str] = SettingsField(
        default_factory=list,
        enum_resolver=instance_attributes_enum,
        title="Instance attributes"
    )
    exposed_knobs: list[str] = SettingsField(
        title="Write Node Exposed Knobs",
        default_factory=list
    )
    prenodes: list[PrenodeModel] = SettingsField(
        default_factory=list,
        title="Preceding nodes",
    )

    @validator("prenodes")
    def ensure_unique_names(cls, value):
        """Ensure name fields within the lists have unique names."""
        ensure_unique_names(value)
        return value


class CreateWriteImageModel(BaseSettingsModel):
    temp_rendering_path_template: str = SettingsField(
        title="Temporary rendering path template"
    )
    default_variants: list[str] = SettingsField(
        title="Default variants",
        default_factory=list
    )
    instance_attributes: list[str] = SettingsField(
        default_factory=list,
        enum_resolver=instance_attributes_enum,
        title="Instance attributes"
    )
    exposed_knobs: list[str] = SettingsField(
        title="Write Node Exposed Knobs",
        default_factory=list
    )
    prenodes: list[PrenodeModel] = SettingsField(
        default_factory=list,
        title="Preceding nodes",
    )

    @validator("prenodes")
    def ensure_unique_names(cls, value):
        """Ensure name fields within the lists have unique names."""
        ensure_unique_names(value)
        return value


class CreatorPluginsSettings(BaseSettingsModel):
    CreateWriteRender: CreateWriteRenderModel = SettingsField(
        default_factory=CreateWriteRenderModel,
        title="Create Write Render"
    )
    CreateWritePrerender: CreateWritePrerenderModel = SettingsField(
        default_factory=CreateWritePrerenderModel,
        title="Create Write Prerender"
    )
    CreateWriteImage: CreateWriteImageModel = SettingsField(
        default_factory=CreateWriteImageModel,
        title="Create Write Image"
    )


DEFAULT_CREATE_SETTINGS = {
    "CreateWriteRender": {
        "temp_rendering_path_template": "{work}/renders/nuke/{product[name]}/{product[name]}.{frame}.{ext}",
        "default_variants": [
            "Main",
            "Mask"
        ],
        "instance_attributes": [
            "reviewable",
            "farm_rendering"
        ],
        "exposed_knobs": [],
        "prenodes": [
            {
                "name": "Reformat01",
                "nodeclass": "Reformat",
                "dependent": "",
                "knobs": [
                    {
                        "type": "text",
                        "name": "resize",
                        "text": "none"
                    },
                    {
                        "type": "boolean",
                        "name": "black_outside",
                        "boolean": True
                    }
                ]
            }
        ]
    },
    "CreateWritePrerender": {
        "temp_rendering_path_template": "{work}/renders/nuke/{product[name]}/{product[name]}.{frame}.{ext}",
        "default_variants": [
            "Key01",
            "Bg01",
            "Fg01",
            "Branch01",
            "Part01"
        ],
        "instance_attributes": [
            "farm_rendering",
            "use_range_limit"
        ],
        "exposed_knobs": [],
        "prenodes": []
    },
    "CreateWriteImage": {
        "temp_rendering_path_template": "{work}/renders/nuke/{product[name]}/{product[name]}.{ext}",
        "default_variants": [
            "StillFrame",
            "MPFrame",
            "LayoutFrame"
        ],
        "instance_attributes": [
            "use_range_limit"
        ],
        "exposed_knobs": [],
        "prenodes": [
            {
                "name": "FrameHold01",
                "nodeclass": "FrameHold",
                "dependent": "",
                "knobs": [
                    {
                        "type": "expression",
                        "name": "first_frame",
                        "expression": "parent.first"
                    }
                ]
            }
        ]
    }
}
