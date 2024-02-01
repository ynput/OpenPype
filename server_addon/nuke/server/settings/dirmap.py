from ayon_server.settings import BaseSettingsModel, SettingsField


class DirmapPathsSubmodel(BaseSettingsModel):
    _layout = "compact"
    source_path: list[str] = SettingsField(
        default_factory=list,
        title="Source Paths"
    )
    destination_path: list[str] = SettingsField(
        default_factory=list,
        title="Destination Paths"
    )


class DirmapSettings(BaseSettingsModel):
    """Nuke color management project settings."""
    _isGroup: bool = True

    enabled: bool = SettingsField(title="enabled")
    paths: DirmapPathsSubmodel = SettingsField(
        default_factory=DirmapPathsSubmodel,
        title="Dirmap Paths"
    )


DEFAULT_DIRMAP_SETTINGS = {
    "enabled": False,
    "paths": {
        "source_path": [],
        "destination_path": []
    }
}
