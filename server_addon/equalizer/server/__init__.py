from ayon_server.addons import BaseServerAddon

from .settings import EqualizerSettings, DEFAULT_EQUALIZER_SETTING
from .version import __version__


class Equalizer(BaseServerAddon):
    name = "equalizer"
    title = "3DEqualizer"
    version = __version__

    settings_model = EqualizerSettings

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_EQUALIZER_SETTING)
