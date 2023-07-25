from typing import Type

from ayon_server.addons import BaseServerAddon

from .version import __version__
from .settings import TvpaintSettings, DEFAULT_VALUES


class TvpaintAddon(BaseServerAddon):
    name = "tvpaint"
    title = "TVPaint"
    version = __version__
    settings_model: Type[TvpaintSettings] = TvpaintSettings


    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_VALUES)
