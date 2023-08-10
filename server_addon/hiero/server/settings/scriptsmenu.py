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


class ScriptsmenuSettings(BaseSettingsModel):
    """Nuke script menu project settings."""
    _isGroup = True

    """# TODO: enhance settings with host api:
    - in api rename key `name` to `menu_name`
    """
    name: str = Field(title="Menu name")
    definition: list[ScriptsmenuSubmodel] = Field(
        default_factory=list,
        title="Definition",
        description="Scriptmenu Items Definition")


DEFAULT_SCRIPTSMENU_SETTINGS = {
    "name": "OpenPype Tools",
    "definition": [
        {
            "type": "action",
            "sourcetype": "python",
            "title": "OpenPype Docs",
            "command": "import webbrowser;webbrowser.open(url='https://openpype.io/docs/artist_hosts_hiero')",
            "tooltip": "Open the OpenPype Hiero user doc page"
        }
    ]
}
