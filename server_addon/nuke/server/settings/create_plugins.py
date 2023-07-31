from pydantic import validator, Field
from ayon_server.settings import (
    BaseSettingsModel,
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
    # TODO: missing in host api
    # - good for `dependency`
    name: str = Field(
        title="Node name"
    )

    # TODO: `nodeclass` should be renamed to `nuke_node_class`
    nodeclass: str = Field(
        "",
        title="Node class"
    )
    dependent: str = Field(
        "",
        title="Incoming dependency"
    )

    """# TODO: Changes in host api:
    - Need complete rework of knob types in nuke integration.
    - We could not support v3 style of settings.
    """
    knobs: list[KnobModel] = Field(
        title="Knobs",
    )

    @validator("knobs")
    def ensure_unique_names(cls, value):
        """Ensure name fields within the lists have unique names."""
        ensure_unique_names(value)
        return value


class CreateWriteRenderModel(BaseSettingsModel):
    temp_rendering_path_template: str = Field(
        title="Temporary rendering path template"
    )
    default_variants: list[str] = Field(
        title="Default variants",
        default_factory=list
    )
    instance_attributes: list[str] = Field(
        default_factory=list,
        enum_resolver=instance_attributes_enum,
        title="Instance attributes"
    )

    """# TODO: Changes in host api:
    - prenodes key was originally dict and now is list
      (we could not support v3 style of settings)
    """
    prenodes: list[PrenodeModel] = Field(
        title="Preceding nodes",
    )

    @validator("prenodes")
    def ensure_unique_names(cls, value):
        """Ensure name fields within the lists have unique names."""
        ensure_unique_names(value)
        return value


class CreateWritePrerenderModel(BaseSettingsModel):
    temp_rendering_path_template: str = Field(
        title="Temporary rendering path template"
    )
    default_variants: list[str] = Field(
        title="Default variants",
        default_factory=list
    )
    instance_attributes: list[str] = Field(
        default_factory=list,
        enum_resolver=instance_attributes_enum,
        title="Instance attributes"
    )

    """# TODO: Changes in host api:
    - prenodes key was originally dict and now is list
      (we could not support v3 style of settings)
    """
    prenodes: list[PrenodeModel] = Field(
        title="Preceding nodes",
    )

    @validator("prenodes")
    def ensure_unique_names(cls, value):
        """Ensure name fields within the lists have unique names."""
        ensure_unique_names(value)
        return value


class CreateWriteImageModel(BaseSettingsModel):
    temp_rendering_path_template: str = Field(
        title="Temporary rendering path template"
    )
    default_variants: list[str] = Field(
        title="Default variants",
        default_factory=list
    )
    instance_attributes: list[str] = Field(
        default_factory=list,
        enum_resolver=instance_attributes_enum,
        title="Instance attributes"
    )

    """# TODO: Changes in host api:
    - prenodes key was originally dict and now is list
      (we could not support v3 style of settings)
    """
    prenodes: list[PrenodeModel] = Field(
        title="Preceding nodes",
    )

    @validator("prenodes")
    def ensure_unique_names(cls, value):
        """Ensure name fields within the lists have unique names."""
        ensure_unique_names(value)
        return value


class CreatorPluginsSettings(BaseSettingsModel):
    CreateWriteRender: CreateWriteRenderModel = Field(
        default_factory=CreateWriteRenderModel,
        title="Create Write Render"
    )
    CreateWritePrerender: CreateWritePrerenderModel = Field(
        default_factory=CreateWritePrerenderModel,
        title="Create Write Prerender"
    )
    CreateWriteImage: CreateWriteImageModel = Field(
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
