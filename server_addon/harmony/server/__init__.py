from ayon_server.addons import BaseServerAddon

from .settings import HarmonySettings, DEFAULT_HARMONY_SETTING
from .version import __version__


class Harmony(BaseServerAddon):
    name = "harmony"
    title = "Harmony"
    version = __version__

    settings_model = HarmonySettings

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_HARMONY_SETTING)
