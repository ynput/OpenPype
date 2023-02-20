import os
from openpype.modules import OpenPypeModule, IHostAddon

HARMONY_HOST_DIR = os.path.dirname(os.path.abspath(__file__))


class HarmonyAddon(OpenPypeModule, IHostAddon):
    name = "harmony"
    host_name = "harmony"

    def initialize(self, module_settings):
        self.enabled = True

    def add_implementation_envs(self, env, _app):
        """Modify environments to contain all required for implementation."""
        openharmony_path = os.path.join(
            HARMONY_HOST_DIR, "vendor", "OpenHarmony"
        )
        # TODO check if is already set? What to do if is already set?
        env["LIB_OPENHARMONY_PATH"] = openharmony_path

    def get_workfile_extensions(self):
        return [".zip"]
