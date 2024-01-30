from ayon_server.settings import BaseSettingsModel, SettingsField

from .imageio import TrayPublisherImageIOModel
from .simple_creators import (
    SimpleCreatorPlugin,
    DEFAULT_SIMPLE_CREATORS,
)
from .editorial_creators import (
    TraypublisherEditorialCreatorPlugins,
    DEFAULT_EDITORIAL_CREATORS,
)
from .creator_plugins import (
    TrayPublisherCreatePluginsModel,
    DEFAULT_CREATORS,
)
from .publish_plugins import (
    TrayPublisherPublishPlugins,
    DEFAULT_PUBLISH_PLUGINS,
)


class TraypublisherSettings(BaseSettingsModel):
    """Traypublisher Project Settings."""
    imageio: TrayPublisherImageIOModel = SettingsField(
        default_factory=TrayPublisherImageIOModel,
        title="Color Management (ImageIO)"
    )
    simple_creators: list[SimpleCreatorPlugin] = SettingsField(
        title="Simple Create Plugins",
        default_factory=SimpleCreatorPlugin,
    )
    editorial_creators: TraypublisherEditorialCreatorPlugins = SettingsField(
        title="Editorial Creators",
        default_factory=TraypublisherEditorialCreatorPlugins,
    )
    create: TrayPublisherCreatePluginsModel = SettingsField(
        title="Create",
        default_factory=TrayPublisherCreatePluginsModel
    )
    publish: TrayPublisherPublishPlugins = SettingsField(
        title="Publish Plugins",
        default_factory=TrayPublisherPublishPlugins
    )


DEFAULT_TRAYPUBLISHER_SETTING = {
    "simple_creators": DEFAULT_SIMPLE_CREATORS,
    "editorial_creators": DEFAULT_EDITORIAL_CREATORS,
    "create": DEFAULT_CREATORS,
    "publish": DEFAULT_PUBLISH_PLUGINS,
}
