from ayon_server.settings import BaseSettingsModel, SettingsField

from .imageio import (
    ImageIOSettings,
    DEFAULT_IMAGEIO_SETTINGS
)
from .create_plugins import (
    CreatorPluginsSettings,
    DEFAULT_CREATE_SETTINGS
)
from .loader_plugins import (
    LoaderPuginsModel,
    DEFAULT_LOADER_PLUGINS_SETTINGS
)
from .publish_plugins import (
    PublishPuginsModel,
    DEFAULT_PUBLISH_PLUGIN_SETTINGS
)
from .scriptsmenu import (
    ScriptsmenuSettings,
    DEFAULT_SCRIPTSMENU_SETTINGS
)
from .filters import PublishGUIFilterItemModel


class HieroSettings(BaseSettingsModel):
    """Nuke addon settings."""

    imageio: ImageIOSettings = SettingsField(
        default_factory=ImageIOSettings,
        title="Color Management (imageio)",
    )

    create: CreatorPluginsSettings = SettingsField(
        default_factory=CreatorPluginsSettings,
        title="Creator Plugins",
    )
    load: LoaderPuginsModel = SettingsField(
        default_factory=LoaderPuginsModel,
        title="Loader plugins"
    )
    publish: PublishPuginsModel = SettingsField(
        default_factory=PublishPuginsModel,
        title="Publish plugins"
    )
    scriptsmenu: ScriptsmenuSettings = SettingsField(
        default_factory=ScriptsmenuSettings,
        title="Scripts Menu Definition",
    )
    filters: list[PublishGUIFilterItemModel] = SettingsField(
        default_factory=list
    )


DEFAULT_VALUES = {
    "imageio": DEFAULT_IMAGEIO_SETTINGS,
    "create": DEFAULT_CREATE_SETTINGS,
    "load": DEFAULT_LOADER_PLUGINS_SETTINGS,
    "publish": DEFAULT_PUBLISH_PLUGIN_SETTINGS,
    "scriptsmenu": DEFAULT_SCRIPTSMENU_SETTINGS,
    "filters": [],
}
