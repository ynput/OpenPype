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

    def add_implementation_envs(self, env, _app):
        # Set default values if are not already set via settings
        defaults = {
            "OPENPYPE_LOG_NO_COLORS": "Yes"
        }
        for key, value in defaults.items():
            if not env.get(key):
                env[key] = value

    def get_workfile_extensions(self):
        return [".comp"]
