from typing import Type

from ayon_server.addons import BaseServerAddon

from .version import __version__
from .settings import BlenderSettings, DEFAULT_VALUES


class BlenderAddon(BaseServerAddon):
    name = "blender"
    title = "Blender"
    version = __version__
    settings_model: Type[BlenderSettings] = BlenderSettings
    frontend_scopes = {}
    services = {}

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_VALUES)
