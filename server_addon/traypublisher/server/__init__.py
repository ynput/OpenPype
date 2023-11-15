from ayon_server.addons import BaseServerAddon

from .version import __version__
from .settings import TraypublisherSettings, DEFAULT_TRAYPUBLISHER_SETTING


class Traypublisher(BaseServerAddon):
    name = "traypublisher"
    title = "TrayPublisher"
    version = __version__

    settings_model = TraypublisherSettings

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_TRAYPUBLISHER_SETTING)
