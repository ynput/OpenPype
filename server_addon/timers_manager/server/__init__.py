from typing import Type

from ayon_server.addons import BaseServerAddon

from .version import __version__
from .settings import TimersManagerSettings


class TimersManagerAddon(BaseServerAddon):
    name = "timers_manager"
    version = __version__
    title = "Timers Manager"
    settings_model: Type[TimersManagerSettings] = TimersManagerSettings
