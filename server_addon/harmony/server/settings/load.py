from pydantic import Field, validator
from ayon_server.settings import BaseSettingsModel


class ImageSequenceLoaderModel(BaseSettingsModel):
    family: list[str] = Field(
        default_factory=list,
        title="Families"
    )
    representations: list[str] = Field(
        default_factory=list,
        title="Representations"
    )


class HarmonyLoadModel(BaseSettingsModel):
    ImageSequenceLoader: ImageSequenceLoaderModel = Field(
        default_factory=ImageSequenceLoaderModel,
        title="Load Image Sequence"
    )
