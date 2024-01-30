from ayon_server.settings import BaseSettingsModel, SettingsField


class ClockifySettings(BaseSettingsModel):
    workspace_name: str = SettingsField(
        "",
        title="Workspace name",
        scope=["studio"]
    )
