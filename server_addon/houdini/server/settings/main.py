from pydantic import Field
from ayon_server.settings import BaseSettingsModel
from .general import (
    GeneralSettingsModel,
    DEFAULT_GENERAL_SETTINGS
)
from .imageio import (
    HoudiniImageIOModel,
    DEFAULT_IMAGEIO_SETTINGS
)
from .shelves import ShelvesModel
from .create import (
    CreatePluginsModel,
    DEFAULT_HOUDINI_CREATE_SETTINGS
)
from .publish import (
    PublishPluginsModel,
    DEFAULT_HOUDINI_PUBLISH_SETTINGS,
)


class HoudiniSettings(BaseSettingsModel):
    general: GeneralSettingsModel = Field(
        default_factory=GeneralSettingsModel,
        title="General"
    )
    imageio: HoudiniImageIOModel = Field(
        default_factory=HoudiniImageIOModel,
        title="Color Management (ImageIO)"
    )
    shelves: list[ShelvesModel] = Field(
        default_factory=list,
        title="Shelves Manager",
    )
    create: CreatePluginsModel = Field(
        default_factory=CreatePluginsModel,
        title="Creator Plugins",
    )
    publish: PublishPluginsModel = Field(
        default_factory=PublishPluginsModel,
        title="Publish Plugins",
    )


DEFAULT_VALUES = {
    "general": DEFAULT_GENERAL_SETTINGS,
    "imageio": DEFAULT_IMAGEIO_SETTINGS,
    "shelves": [],
    "create": DEFAULT_HOUDINI_CREATE_SETTINGS,
    "publish": DEFAULT_HOUDINI_PUBLISH_SETTINGS
}
