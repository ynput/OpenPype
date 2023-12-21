from pydantic import Field
from ayon_server.settings import BaseSettingsModel
from .imageio import ImageIOSettings, DEFAULT_IMAGEIO_SETTINGS


class ShelvesSettingsModel(BaseSettingsModel):
    _layout = "compact"
    name: str = Field(title="Name")
    value: str = Field(title="Path")


class SubstancePainterSettings(BaseSettingsModel):
    imageio: ImageIOSettings = Field(
        default_factory=ImageIOSettings,
        title="Color Management (ImageIO)"
    )
    shelves: list[ShelvesSettingsModel] = Field(
        default_factory=list,
        title="Shelves"
    )


DEFAULT_SPAINTER_SETTINGS = {
    "imageio": DEFAULT_IMAGEIO_SETTINGS,
    "shelves": []
}
