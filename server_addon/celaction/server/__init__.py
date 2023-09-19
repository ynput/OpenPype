from typing import Type

from ayon_server.addons import BaseServerAddon

from .version import __version__
from .settings import CelActionSettings, DEFAULT_VALUES


class CelActionAddon(BaseServerAddon):
    name = "celaction"
    title = "CelAction"
    version = __version__
    settings_model: Type[CelActionSettings] = CelActionSettings
    frontend_scopes = {}
    services = {}

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_VALUES)
