from openpype.modules import OpenPypeModule
from openpype.modules.interfaces import IHostAddon


class AfterEffectsAddon(OpenPypeModule, IHostAddon):
    name = "aftereffects"
    host_name = "aftereffects"

    def initialize(self, module_settings):
        self.enabled = True

    def add_implementation_envs(self, env, _app):
        """Modify environments to contain all required for implementation."""
        defaults = {
            "OPENPYPE_LOG_NO_COLORS": "True",
            "WEBSOCKET_URL": "ws://localhost:8097/ws/"
        }
        for key, value in defaults.items():
            if not env.get(key):
                env[key] = value

    def get_workfile_extensions(self):
        return [".aep"]
