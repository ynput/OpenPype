import os
from openpype.modules import OpenPypeModule
from openpype.modules.interfaces import IHostModule

PHOTOSHOP_HOST_DIR = os.path.dirname(os.path.abspath(__file__))


class PhotoshopAddon(OpenPypeModule, IHostModule):
    name = "photoshop"
    host_name = "photoshop"

    def initialize(self, module_settings):
        self.enabled = True

    def add_implementation_envs(self, env, _app):
        """Modify environments to contain all required for implementation."""
        defaults = {
            "OPENPYPE_LOG_NO_COLORS": "True",
            "WEBSOCKET_URL": "ws://localhost:8099/ws/"
        }
        for key, value in defaults.items():
            if not env.get(key):
                env[key] = value

    def get_workfile_extensions(self):
        return [".psd", ".psb"]
