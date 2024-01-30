from ayon_server.settings import BaseSettingsModel, SettingsField
from .general import (
    GeneralSettingsModel,
    DEFAULT_GENERAL_SETTINGS
)
from .imageio import HoudiniImageIOModel
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
    general: GeneralSettingsModel = SettingsField(
        default_factory=GeneralSettingsModel,
        title="General"
    )
    imageio: HoudiniImageIOModel = SettingsField(
        default_factory=HoudiniImageIOModel,
        title="Color Management (ImageIO)"
    )
    shelves: list[ShelvesModel] = SettingsField(
        default_factory=list,
        title="Shelves Manager",
    )
    create: CreatePluginsModel = SettingsField(
        default_factory=CreatePluginsModel,
        title="Creator Plugins",
    )
    publish: PublishPluginsModel = SettingsField(
        default_factory=PublishPluginsModel,
        title="Publish Plugins",
    )


DEFAULT_VALUES = {
    "general": DEFAULT_GENERAL_SETTINGS,
    "shelves": [],
    "create": DEFAULT_HOUDINI_CREATE_SETTINGS,
    "publish": DEFAULT_HOUDINI_PUBLISH_SETTINGS
}
