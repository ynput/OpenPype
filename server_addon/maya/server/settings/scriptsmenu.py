from pydantic import Field

from ayon_server.settings import BaseSettingsModel


class ScriptsmenuSubmodel(BaseSettingsModel):
    """Item Definition"""
    _isGroup = True
    type: str = Field(title="Type")
    command: str = Field(title="Command")
    sourcetype: str = Field(title="Source Type")
    title: str = Field(title="Title")
    tooltip: str = Field(title="Tooltip")
    tags: list[str] = Field(default_factory=list, title="A list of tags")


class ScriptsmenuModel(BaseSettingsModel):
    _isGroup = True

    name: str = Field(title="Menu Name")
    definition: list[ScriptsmenuSubmodel] = Field(
        default_factory=list,
        title="Menu Definition",
        description="Scriptmenu Items Definition"
    )


DEFAULT_SCRIPTSMENU_SETTINGS = {
    "name": "OpenPype Tools",
    "definition": [
        {
            "type": "action",
            "command": "import openpype.hosts.maya.api.commands as op_cmds; op_cmds.edit_shader_definitions()",
            "sourcetype": "python",
            "title": "Edit shader name definitions",
            "tooltip": "Edit shader name definitions used in validation and renaming.",
            "tags": [
                "pipeline",
                "shader"
            ]
        }
    ]
}
