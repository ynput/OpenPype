from ayon_server.settings import BaseSettingsModel, SettingsField


class ScriptsmenuSubmodel(BaseSettingsModel):
    """Item Definition"""
    _isGroup = True
    type: str = SettingsField(title="Type")
    command: str = SettingsField(title="Command")
    sourcetype: str = SettingsField(title="Source Type")
    title: str = SettingsField(title="Title")
    tooltip: str = SettingsField(title="Tooltip")
    tags: list[str] = SettingsField(
        default_factory=list, title="A list of tags"
    )


class ScriptsmenuModel(BaseSettingsModel):
    _isGroup = True

    name: str = SettingsField(title="Menu Name")
    definition: list[ScriptsmenuSubmodel] = SettingsField(
        default_factory=list,
        title="Menu Definition",
        description="Scriptmenu Items Definition"
    )


DEFAULT_SCRIPTSMENU_SETTINGS = {
    "name": "Custom Tools",
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
