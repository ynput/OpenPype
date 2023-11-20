from ayon_server.settings import Field, BaseSettingsModel

from .imageio import FlameImageIOModel, DEFAULT_IMAGEIO_SETTINGS
from .create_plugins import CreatePluginsModel, DEFAULT_CREATE_SETTINGS
from .publish_plugins import PublishPluginsModel, DEFAULT_PUBLISH_SETTINGS
from .loader_plugins import LoaderPluginsModel, DEFAULT_LOADER_SETTINGS


class FlameSettings(BaseSettingsModel):
    imageio: FlameImageIOModel = Field(
        default_factory=FlameImageIOModel,
        title="Color Management (ImageIO)"
    )
    create: CreatePluginsModel = Field(
        default_factory=CreatePluginsModel,
        title="Create plugins"
    )
    publish: PublishPluginsModel = Field(
        default_factory=PublishPluginsModel,
        title="Publish plugins"
    )
    load: LoaderPluginsModel = Field(
        default_factory=LoaderPluginsModel,
        title="Loader plugins"
    )


DEFAULT_VALUES = {
    "imageio": DEFAULT_IMAGEIO_SETTINGS,
    "create": DEFAULT_CREATE_SETTINGS,
    "publish": DEFAULT_PUBLISH_SETTINGS,
    "load": DEFAULT_LOADER_SETTINGS
}
