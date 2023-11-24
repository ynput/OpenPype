from typing import Type

from ayon_server.addons import BaseServerAddon

from .version import __version__
from .settings import ClockifySettings


class ClockifyAddon(BaseServerAddon):
    name = "clockify"
    title = "Clockify"
    version = __version__
    settings_model: Type[ClockifySettings] = ClockifySettings
    frontend_scopes = {}
    services = {}
