"""Maya Addon Module"""
from ayon_server.addons import BaseServerAddon

from .settings.main import MayaSettings, DEFAULT_MAYA_SETTING
from .version import __version__


class MayaAddon(BaseServerAddon):
    name = "maya"
    title = "Maya"
    version = __version__
    settings_model = MayaSettings

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_MAYA_SETTING)
