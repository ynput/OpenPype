from pydantic import Field
from ayon_server.settings import BaseSettingsModel

from .imageio import AfterEffectsImageIOModel
from .creator_plugins import AfterEffectsCreatorPlugins
from .publish_plugins import (
    AfterEffectsPublishPlugins,
    AE_PUBLISH_PLUGINS_DEFAULTS,
)
from .workfile_builder import WorkfileBuilderPlugin
from .templated_workfile_build import TemplatedWorkfileBuildModel


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
    templated_workfile_build: TemplatedWorkfileBuildModel = Field(
        default_factory=TemplatedWorkfileBuildModel,
        title="Templated Workfile Build Settings"
    )


DEFAULT_AFTEREFFECTS_SETTING = {
    "create": {
        "RenderCreator": {
            "mark_for_review": True,
            "default_variants": [
                "Main"
            ]
        }
    },
    "publish": AE_PUBLISH_PLUGINS_DEFAULTS,
    "workfile_builder": {
        "create_first_version": False,
        "custom_templates": []
    },
    "templated_workfile_build": {
        "profiles": []
    },
}
