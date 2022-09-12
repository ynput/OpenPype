import os
from openpype.modules import OpenPypeModule
from openpype.modules.interfaces import IHostAddon

FUSION_HOST_DIR = os.path.dirname(os.path.abspath(__file__))


class FusionAddon(OpenPypeModule, IHostAddon):
    name = "fusion"
    host_name = "fusion"

    def initialize(self, module_settings):
        self.enabled = True

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [
            os.path.join(FUSION_HOST_DIR, "hooks")
        ]

    def get_workfile_extensions(self):
        return [".comp"]
