from ayon_server.addons import BaseServerAddon

from .settings import PhotoshopSettings, DEFAULT_PHOTOSHOP_SETTING
from .version import __version__


class Photoshop(BaseServerAddon):
    name = "photoshop"
    version = __version__

    settings_model = PhotoshopSettings

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_PHOTOSHOP_SETTING)
