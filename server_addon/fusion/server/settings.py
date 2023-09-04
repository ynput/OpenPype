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


class CreatPluginsModel(BaseSettingsModel):
    CreateSaver: CreateSaverPluginModel = Field(
        default_factory=CreateSaverPluginModel,
        title="Create Saver"
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
            ]
        }
    }
}
