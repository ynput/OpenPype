from pydantic import Field
from ayon_server.settings import BaseSettingsModel

from .creator_plugins import (
    EqualizerCreatorPlugins,
    EQ_CREATORS_PLUGINS_DEFAULTS,
)
# from .publish_plugins import (
#     EqualizerPublishPlugins,
#     EQ_PUBLISH_PLUGINS_DEFAULTS,
# )


class EqualizerSettings(BaseSettingsModel):
    """AfterEffects Project Settings."""

    create: EqualizerCreatorPlugins = Field(
        default_factory=EqualizerCreatorPlugins,
        title="Creator plugins"
    )
    # publish: EqualizerPublishPlugins = Field(
    #     default_factory=EqualizerPublishPlugins,
    #     title="Publish plugins"
    # )


DEFAULT_EQUALIZER_SETTING = {
    "create": EQ_CREATORS_PLUGINS_DEFAULTS,
    # "publish": EQ_PUBLISH_PLUGINS_DEFAULTS,
}
