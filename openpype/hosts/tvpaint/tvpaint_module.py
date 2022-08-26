import os
from openpype.modules import OpenPypeModule
from openpype.modules.interfaces import IHostAddon

TVPAINT_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_launch_script_path():
    return os.path.join(
        TVPAINT_ROOT_DIR,
        "api",
        "launch_script.py"
    )


class TVPaintModule(OpenPypeModule, IHostAddon):
    name = "tvpaint"
    host_name = "tvpaint"

    def initialize(self, module_settings):
        self.enabled = True

    def add_implementation_envs(self, env, _app):
        """Modify environments to contain all required for implementation."""

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
            os.path.join(TVPAINT_ROOT_DIR, "hooks")
        ]

    def get_workfile_extensions(self):
        return [".tvpp"]
