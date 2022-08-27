import os

from openpype.modules import OpenPypeModule
from openpype.modules.interfaces import IHostAddon

from .utils import RESOLVE_ROOT_DIR


class ResolveAddon(OpenPypeModule, IHostAddon):
    name = "resolve"
    host_name = "resolve"

    def initialize(self, module_settings):
        self.enabled = True

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [
            os.path.join(RESOLVE_ROOT_DIR, "hooks")
        ]

    def get_workfile_extensions(self):
        return [".drp"]
