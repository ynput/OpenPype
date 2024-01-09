from pydantic import Field
from ayon_server.settings import (
    BaseSettingsModel,
)

from .imageio import FusionImageIOModel


class CopyFusionSettingsModel(BaseSettingsModel):
    copy_path: str = Field("", title="Local Fusion profile directory")
    copy_status: bool = Field(title="Copy profile on first launch")
    force_sync: bool = Field(title="Resync profile on each launch")


def _create_saver_instance_attributes_enum():
    return [
        {
            "value": "reviewable",
            "label": "Reviewable"
        },
        {
            "value": "farm_rendering",
            "label": "Farm rendering"
        }
    ]


def _image_format_enum():
    return [
        {"value": "exr", "label": "exr"},
        {"value": "tga", "label": "tga"},
        {"value": "png", "label": "png"},
        {"value": "tif", "label": "tif"},
        {"value": "jpg", "label": "jpg"},
    ]


def _frame_range_options_enum():
    return [
        {"value": "asset_db", "label": "Current asset context"},
        {"value": "render_range", "label": "From render in/out"},
        {"value": "comp_range", "label": "From composition timeline"},
    ]


class CreateSaverPluginModel(BaseSettingsModel):
    _isGroup = True
    temp_rendering_path_template: str = Field(
        "", title="Temporary rendering path template"
    )
    default_variants: list[str] = Field(
        default_factory=list,
        title="Default variants"
    )
    instance_attributes: list[str] = Field(
        default_factory=list,
        enum_resolver=_create_saver_instance_attributes_enum,
        title="Instance attributes"
    )
    image_format: str = Field(
        enum_resolver=_image_format_enum,
        title="Output Image Format"
    )


class CreateSaverModel(CreateSaverPluginModel):
    default_frame_range_option: str = Field(
        default="asset_db",
        enum_resolver=_frame_range_options_enum,
        title="Default frame range source"
    )


class CreateImageSaverModel(CreateSaverPluginModel):
    default_frame: int = Field(
        0,
        title="Default rendered frame"
    )
class CreatPluginsModel(BaseSettingsModel):
    CreateSaver: CreateSaverModel = Field(
        default_factory=CreateSaverModel,
        title="Create Saver",
        description="Creator for render product type (eg. sequence)"
    )
    CreateImageSaver: CreateImageSaverModel = Field(
        default_factory=CreateImageSaverModel,
        title="Create Image Saver",
        description="Creator for image product type (eg. single)"
    )


class FusionSettings(BaseSettingsModel):
    imageio: FusionImageIOModel = Field(
        default_factory=FusionImageIOModel,
        title="Color Management (ImageIO)"
    )
    copy_fusion_settings: CopyFusionSettingsModel = Field(
        default_factory=CopyFusionSettingsModel,
        title="Local Fusion profile settings"
    )
    create: CreatPluginsModel = Field(
        default_factory=CreatPluginsModel,
        title="Creator plugins"
    )


DEFAULT_VALUES = {
    "imageio": {
        "ocio_config": {
            "enabled": False,
            "filepath": []
        },
        "file_rules": {
            "enabled": False,
            "rules": []
        }
    },
    "copy_fusion_settings": {
        "copy_path": "~/.openpype/hosts/fusion/profiles",
        "copy_status": False,
        "force_sync": False
    },
    "create": {
        "CreateSaver": {
            "temp_rendering_path_template": "{workdir}/renders/fusion/{product[name]}/{product[name]}.{frame}.{ext}",
            "default_variants": [
                "Main",
                "Mask"
            ],
            "instance_attributes": [
                "reviewable",
                "farm_rendering"
            ],
            "image_format": "exr"
            "image_format": "exr",
            "default_frame_range_option": "asset_db"
        },
        "CreateImageSaver": {
            "temp_rendering_path_template": "{workdir}/renders/fusion/{product[name]}/{product[name]}.{ext}",
            "default_variants": [
                "Main",
                "Mask"
            ],
            "instance_attributes": [
                "reviewable",
                "farm_rendering"
            ],
            "image_format": "exr"
            "image_format": "exr",
            "default_frame": 0
        }
    }
}
