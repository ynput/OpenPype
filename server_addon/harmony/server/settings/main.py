from ayon_server.settings import BaseSettingsModel, SettingsField

from .imageio import HarmonyImageIOModel
from .publish_plugins import HarmonyPublishPlugins


class HarmonySettings(BaseSettingsModel):
    """Harmony Project Settings."""

    imageio: HarmonyImageIOModel = SettingsField(
        default_factory=HarmonyImageIOModel,
        title="OCIO config"
    )
    publish: HarmonyPublishPlugins = SettingsField(
        default_factory=HarmonyPublishPlugins,
        title="Publish plugins"
    )


DEFAULT_HARMONY_SETTING = {
    "load": {
        "ImageSequenceLoader": {
            "family": [
                "shot",
                "render",
                "image",
                "plate",
                "reference"
            ],
            "representations": [
                "jpeg",
                "png",
                "jpg"
            ]
        }
    },
    "publish": {
        "CollectPalettes": {
            "allowed_tasks": [
                ".*"
            ]
        },
        "ValidateAudio": {
            "enabled": True,
            "optional": True,
            "active": True
        },
        "ValidateContainers": {
            "enabled": True,
            "optional": True,
            "active": True
        },
        "ValidateSceneSettings": {
            "enabled": True,
            "optional": True,
            "active": True,
            "frame_check_filter": [],
            "skip_resolution_check": [],
            "skip_timelines_check": []
        }
    }
}
