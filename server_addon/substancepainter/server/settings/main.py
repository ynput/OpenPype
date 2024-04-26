from ayon_server.settings import BaseSettingsModel, SettingsField
from .imageio import ImageIOSettings, DEFAULT_IMAGEIO_SETTINGS
from .load_plugins import LoadersModel, DEFAULT_LOADER_SETTINGS


class ShelvesSettingsModel(BaseSettingsModel):
    _layout = "compact"
    name: str = SettingsField(title="Name")
    value: str = SettingsField(title="Path")


class SubstancePainterSettings(BaseSettingsModel):
    imageio: ImageIOSettings = SettingsField(
        default_factory=ImageIOSettings,
        title="Color Management (ImageIO)"
    )
    shelves: list[ShelvesSettingsModel] = SettingsField(
        default_factory=list,
        title="Shelves"
    )
    load: LoadersModel = SettingsField(
        default_factory=DEFAULT_LOADER_SETTINGS, title="Loaders")


DEFAULT_SPAINTER_SETTINGS = {
    "imageio": DEFAULT_IMAGEIO_SETTINGS,
    "shelves": [],
    "load": DEFAULT_LOADER_SETTINGS,
}
