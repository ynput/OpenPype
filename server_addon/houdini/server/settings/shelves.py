from pydantic import Field
from ayon_server.settings import (
    BaseSettingsModel,
    MultiplatformPathModel
)


class ShelfToolsModel(BaseSettingsModel):
    """Name and Script Path are mandatory."""
    label: str = Field(title="Name")
    script: str = Field(title="Script Path")
    icon: str = Field( "", title="Icon Path")
    help: str = Field("", title="Help text")


class ShelfDefinitionModel(BaseSettingsModel):
    _layout = "expanded"
    shelf_name: str = Field(title="Shelf name")
    tools_list: list[ShelfToolsModel] = Field(
        default_factory=list,
        title="Shelf Tools"
    )


class ShelvesModel(BaseSettingsModel):
    _layout = "expanded"
    shelf_set_name: str = Field("", title="Shelfs set name")

    shelf_set_source_path: MultiplatformPathModel = Field(
        default_factory=MultiplatformPathModel,
        title="Shelf Set Path (optional)"
    )

    shelf_definition: list[ShelfDefinitionModel] = Field(
        default_factory=list,
        title="Shelf Definitions"
    )
