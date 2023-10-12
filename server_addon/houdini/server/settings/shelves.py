from pydantic import Field
from ayon_server.settings import (
    BaseSettingsModel,
    MultiplatformPathModel,
    MultiplatformPathListModel,
)


class ShelfToolsModel(BaseSettingsModel):
    name: str = Field(title="Name")
    help: str = Field(title="Help text")
    # TODO: The following settings are not compatible with OP
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
