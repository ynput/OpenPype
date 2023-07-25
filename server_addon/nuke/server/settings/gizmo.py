from pydantic import Field
from ayon_server.settings import (
    BaseSettingsModel,
    MultiplatformPathModel,
    MultiplatformPathListModel,
)


class SubGizmoItem(BaseSettingsModel):
    title: str = Field(
        title="Label"
    )
    sourcetype: str = Field(
        title="Type of usage"
    )
    command: str = Field(
        title="Python command"
    )
    icon: str = Field(
        title="Icon Path"
    )
    shortcut: str = Field(
        title="Hotkey"
    )


class GizmoDefinitionItem(BaseSettingsModel):
    gizmo_toolbar_path: str = Field(
        title="Gizmo Menu"
    )
    sub_gizmo_list: list[SubGizmoItem] = Field(
        default_factory=list, title="Sub Gizmo List")


class GizmoItem(BaseSettingsModel):
    """Nuke gizmo item """

    toolbar_menu_name: str = Field(
        title="Toolbar Menu Name"
    )
    gizmo_source_dir: MultiplatformPathListModel = Field(
        default_factory=MultiplatformPathListModel,
        title="Gizmo Directory Path"
    )
    toolbar_icon_path: MultiplatformPathModel = Field(
        default_factory=MultiplatformPathModel,
        title="Toolbar Icon Path"
    )
    gizmo_definition: list[GizmoDefinitionItem] = Field(
        default_factory=list, title="Gizmo Definition")



DEFAULT_GIZMO_ITEM = {
    "toolbar_menu_name": "OpenPype Gizmo",
    "gizmo_source_dir": {
        "windows": [],
        "darwin": [],
        "linux": []
    },
    "toolbar_icon_path": {
        "windows": "",
        "darwin": "",
        "linux": ""
    },
    "gizmo_definition": [
        {
            "gizmo_toolbar_path": "/path/to/menu",
            "sub_gizmo_list": [
                {
                    "sourcetype": "python",
                    "title": "Gizmo Note",
                    "command": "nuke.nodes.StickyNote(label='You can create your own toolbar menu in the Nuke GizmoMenu of OpenPype')",
                    "icon": "",
                    "shortcut": ""
                }
            ]
        }
    ]
}
