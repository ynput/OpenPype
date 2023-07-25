from typing import Type

from ayon_server.addons import BaseServerAddon

from .version import __version__
from .settings import MusterSettings, DEFAULT_VALUES


class MusterAddon(BaseServerAddon):
    name = "muster"
    version = __version__
    title = "Muster"
    settings_model: Type[MusterSettings] = MusterSettings

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_VALUES)
