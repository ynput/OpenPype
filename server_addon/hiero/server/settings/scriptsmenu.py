from ayon_server.settings import BaseSettingsModel, SettingsField


class ScriptsmenuSubmodel(BaseSettingsModel):
    """Item Definition"""
    _isGroup = True

    type: str = SettingsField(title="Type")
    command: str = SettingsField(title="Command")
    sourcetype: str = SettingsField(title="Source Type")
    title: str = SettingsField(title="Title")
    tooltip: str = SettingsField(title="Tooltip")


class ScriptsmenuSettings(BaseSettingsModel):
    """Nuke script menu project settings."""
    _isGroup = True

    """# TODO: enhance settings with host api:
    - in api rename key `name` to `menu_name`
    """
    name: str = SettingsField(title="Menu name")
    definition: list[ScriptsmenuSubmodel] = SettingsField(
        default_factory=list,
        title="Definition",
        description="Scriptmenu Items Definition")


DEFAULT_SCRIPTSMENU_SETTINGS = {
    "name": "Custom Tools",
    "definition": [
        {
            "type": "action",
            "sourcetype": "python",
            "title": "Ayon Hiero Docs",
            "command": "import webbrowser;webbrowser.open(url='https://ayon.ynput.io/docs/addon_hiero_artist')",  # noqa
            "tooltip": "Open the Ayon Hiero user doc page"
        }
    ]
}
