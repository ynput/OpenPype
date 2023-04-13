import os
import sys
from openpype.modules import OpenPypeModule
from openpype.modules.interfaces import IHostAddon

OPENRV_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class OpenRVAddon(OpenPypeModule, IHostAddon):
    name = "openrv"
    host_name = "openrv"

    def initialize(self, module_settings):
        self.enabled = True

    def add_implementation_envs(self, env, app):
        """Modify environments to contain all required for implementation."""
        sys.path.insert(0, os.path.join(os.getenv("OPENPYPE_ROOT"), "vendor", "python"))
        # Set default environments if are not set via settings
        defaults = {
            "OPENPYPE_LOG_NO_COLORS": "True"
        }
        for key, value in defaults.items():
            if not env.get(key):
                env[key] = value

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [
            os.path.join(OPENRV_ROOT_DIR, "hooks")
        ]

    def get_workfile_extensions(self):
        return [".rv"]
