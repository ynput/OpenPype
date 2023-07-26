from pydantic import Field
from ayon_server.settings import BaseSettingsModel

from .imageio import AfterEffectsImageIOModel
from .creator_plugins import AfterEffectsCreatorPlugins
from .publish_plugins import AfterEffectsPublishPlugins
from .workfile_builder import WorkfileBuilderPlugin


class AfterEffectsSettings(BaseSettingsModel):
    """AfterEffects Project Settings."""

    imageio: AfterEffectsImageIOModel = Field(
        default_factory=AfterEffectsImageIOModel,
        title="OCIO config"
    )
    create: AfterEffectsCreatorPlugins = Field(
        default_factory=AfterEffectsCreatorPlugins,
        title="Creator plugins"
    )

    publish: AfterEffectsPublishPlugins = Field(
        default_factory=AfterEffectsPublishPlugins,
        title="Publish plugins"
    )

    workfile_builder: WorkfileBuilderPlugin = Field(
        default_factory=WorkfileBuilderPlugin,
        title="Workfile Builder"
    )


DEFAULT_AFTEREFFECTS_SETTING = {
    "create": {
        "RenderCreator": {
            "mark_for_review": True,
            "defaults": [
                "Main"
            ]
        }
    },
    "publish": {
        "CollectReview": {
            "enabled": True
        },
        "ValidateSceneSettings": {
            "enabled": True,
            "optional": True,
            "active": True,
            "skip_resolution_check": [
                ".*"
            ],
            "skip_timelines_check": [
                ".*"
            ]
        }
    },
    "workfile_builder": {
        "create_first_version": False,
        "custom_templates": []
    }
}
