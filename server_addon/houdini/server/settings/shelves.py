from pydantic import Field
from ayon_server.settings import (
    BaseSettingsModel,
    MultiplatformPathModel
)


class ShelfToolsModel(BaseSettingsModel):
    """Name and Script Path are mandatory."""
    label: str = Field(title="Name")
    script: str = Field(title="Script Path")
    icon: str = Field("", title="Icon Path")
    help: str = Field("", title="Help text")


class ShelfDefinitionModel(BaseSettingsModel):
    _layout = "expanded"
    shelf_name: str = Field(title="Shelf name")
    tools_list: list[ShelfToolsModel] = Field(
        default_factory=list,
        title="Shelf Tools"
    )


class AddShelfFileModel(BaseSettingsModel):
    shelf_set_source_path: MultiplatformPathModel = Field(
        default_factory=MultiplatformPathModel,
        title="Shelf Set Path"
    )


class AddSetAndDefinitionsModel(BaseSettingsModel):
    shelf_set_name: str = Field(title="Shelf Set Name")
    shelf_definition: list[ShelfDefinitionModel] = Field(
        default_factory=list,
        title="Shelves Definitions"
    )


def shelves_enum_options():
    return [
        {
            "value": "add_shelf_file",
            "label": "Add a .shelf file"
        },
        {
            "value": "add_set_and_definitions",
            "label": "Add Shelf Set Name and Shelves Definitions"
        }
    ]


class ShelvesModel(BaseSettingsModel):
    options: str = Field(
        title="Options",
        description="Switch between shelves manager options",
        enum_resolver=shelves_enum_options,
        conditionalEnum=True
    )
    add_shelf_file: AddShelfFileModel = Field(
        title="Add a .shelf file",
        default_factory=AddShelfFileModel
    )
    add_set_and_definitions: AddSetAndDefinitionsModel = Field(
        title="Add Shelf Set Name and Shelves Definitions",
        default_factory=AddSetAndDefinitionsModel
    )
