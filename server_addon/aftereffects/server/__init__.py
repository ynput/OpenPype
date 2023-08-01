from ayon_server.addons import BaseServerAddon

from .settings import AfterEffectsSettings, DEFAULT_AFTEREFFECTS_SETTING
from .version import __version__


class AfterEffects(BaseServerAddon):
    name = "aftereffects"
    title = "AfterEffects"
    version = __version__

    settings_model = AfterEffectsSettings

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_AFTEREFFECTS_SETTING)
