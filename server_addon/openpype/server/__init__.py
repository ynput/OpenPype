from ayon_server.addons import BaseServerAddon

from .version import __version__


class OpenPypeAddon(BaseServerAddon):
    name = "openpype"
    title = "OpenPype"
    version = __version__
