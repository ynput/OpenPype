from ayon_server.addons import BaseServerAddon

from .version import __version__
from .settings import CoreSettings, DEFAULT_VALUES


class CoreAddon(BaseServerAddon):
    name = "core"
    title = "Core"
    version = __version__
    settings_model = CoreSettings

    async def get_default_settings(self):
        settings_model_cls = self.get_settings_model()
        return settings_model_cls(**DEFAULT_VALUES)
