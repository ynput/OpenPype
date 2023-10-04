from ayon_server.settings import Field, BaseSettingsModel

from .imageio import FlameImageIOModel, DEFAULT_IMAGEIO_SETTINGS
from .create_plugins import CreatePuginsModel, DEFAULT_CREATE_SETTINGS
from .publish_plugins import PublishPuginsModel, DEFAULT_PUBLISH_SETTINGS
from .loader_plugins import LoaderPluginsModel, DEFAULT_LOADER_SETTINGS


class FlameSettings(BaseSettingsModel):
    imageio: FlameImageIOModel = Field(
        default_factory=FlameImageIOModel,
        title="Color Management (ImageIO)"
    )
    create: CreatePuginsModel = Field(
        default_factory=CreatePuginsModel,
        title="Create plugins"
    )
    publish: PublishPuginsModel = Field(
        default_factory=PublishPuginsModel,
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
