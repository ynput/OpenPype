from pydantic import Field
from ayon_server.settings import (
    BaseSettingsModel,
    MultiplatformPathModel,
    MultiplatformPathListModel,
)
from .general import (
    GeneralSettingsModel,
    DEFAULT_GENERAL_SETTINGS
)
from .imageio import HoudiniImageIOModel
from .publish_plugins import (
    PublishPluginsModel,
    CreatePluginsModel,
    DEFAULT_HOUDINI_PUBLISH_SETTINGS,
    DEFAULT_HOUDINI_CREATE_SETTINGS
)


class ShelfToolsModel(BaseSettingsModel):
    name: str = Field(title="Name")
    help: str = Field(title="Help text")
    script: MultiplatformPathModel = Field(
        default_factory=MultiplatformPathModel,
        title="Script Path "
    )
    icon: MultiplatformPathModel = Field(
        default_factory=MultiplatformPathModel,
        title="Icon Path "
    )


class ShelfDefinitionModel(BaseSettingsModel):
    _layout = "expanded"
    shelf_name: str = Field(title="Shelf name")
    tools_list: list[ShelfToolsModel] = Field(
        default_factory=list,
        title="Shelf Tools"
    )


class ShelvesModel(BaseSettingsModel):
    _layout = "expanded"
    shelf_set_name: str = Field(title="Shelfs set name")

    shelf_set_source_path: MultiplatformPathListModel = Field(
        default_factory=MultiplatformPathListModel,
        title="Shelf Set Path (optional)"
    )

    shelf_definition: list[ShelfDefinitionModel] = Field(
        default_factory=list,
        title="Shelf Definitions"
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
        title="Houdini Scripts Shelves",
    )

    publish: PublishPluginsModel = Field(
        default_factory=PublishPluginsModel,
        title="Publish Plugins",
    )

    create: CreatePluginsModel = Field(
        default_factory=CreatePluginsModel,
        title="Creator Plugins",
    )


DEFAULT_VALUES = {
    "general": DEFAULT_GENERAL_SETTINGS,
    "shelves": [],
    "create": DEFAULT_HOUDINI_CREATE_SETTINGS,
    "publish": DEFAULT_HOUDINI_PUBLISH_SETTINGS
}
