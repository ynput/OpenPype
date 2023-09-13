import os
from openpype.modules import OpenPypeModule, IHostAddon

EQUALIZER_HOST_DIR = os.path.dirname(os.path.abspath(__file__))


class EqualizerAddon(OpenPypeModule, IHostAddon):
    name = "equalizer"
    host_name = "equalizer"

    def initialize(self, module_settings):
        self.enabled = True

    def add_implementation_envs(self, env, _app):
        # 3dequalizer utilize PYTHON_CUSTOM_SCRIPTS_3DE4 for custom scripts
        # and TDE4_ROOT for its root directory. Note that the custom script
        # paths are semicolon separated even on Windows.

        startup_path = os.path.join(EQUALIZER_HOST_DIR, "startup")
        if "PYTHON_CUSTOM_SCRIPTS_3DE4" in env:
            startup_path = env["PYTHON_CUSTOM_SCRIPTS_3DE4"] + ":" + startup_path

        env["PYTHON_CUSTOM_SCRIPTS_3DE4"] = startup_path

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [
            os.path.join(EQUALIZER_HOST_DIR, "hooks")
        ]

    def get_workfile_extensions(self):
        return [".3de"]
