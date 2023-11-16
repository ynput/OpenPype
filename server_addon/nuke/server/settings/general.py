from pydantic import Field
from ayon_server.settings import BaseSettingsModel


class MenuShortcut(BaseSettingsModel):
    """Nuke general project settings."""

    create: str = Field(
        title="Create..."
    )
    publish: str = Field(
        title="Publish..."
    )
    load: str = Field(
        title="Load..."
    )
    manage: str = Field(
        title="Manage..."
    )
    build_workfile: str = Field(
        title="Build Workfile..."
    )


class GeneralSettings(BaseSettingsModel):
    """Nuke general project settings."""

    menu: MenuShortcut = Field(
        default_factory=MenuShortcut,
        title="Menu Shortcuts",
    )


DEFAULT_GENERAL_SETTINGS = {
    "menu": {
        "create": "ctrl+alt+c",
        "publish": "ctrl+alt+p",
        "load": "ctrl+alt+l",
        "manage": "ctrl+alt+m",
        "build_workfile": "ctrl+alt+b"
    }
}
