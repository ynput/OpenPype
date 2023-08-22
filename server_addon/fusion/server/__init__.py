from typing import Type

from ayon_server.addons import BaseServerAddon

from .version import __version__
from .settings import FusionSettings, DEFAULT_VALUES


class FusionAddon(BaseServerAddon):
    name = "fusion"
    title = "Fusion"
    version = __version__
    settings_model: Type[FusionSettings] = FusionSettings
    frontend_scopes = {}
    services = {}

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_VALUES)
