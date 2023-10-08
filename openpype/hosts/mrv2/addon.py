import os
from openpype.modules import OpenPypeModule, IHostAddon

MRV2_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class Mrv2Addon(OpenPypeModule, IHostAddon):
    name = "mrv2"
    host_name = "mrv2"

    def initialize(self, module_settings):
        self.enabled = True

    def add_implementation_envs(self, env, _app):
        # Add MRV2 OpenPype plugin to MRV2_PYTHON_PLUGINS
        startup_path = os.path.join(MRV2_ROOT_DIR, "startup")
        existing = env.get("MRV2_PYTHON_PLUGINS")
        if existing:
            value = os.pathsep.join([startup_path, existing])
        else:
            value = startup_path
        env["MRV2_PYTHON_PLUGINS"] = value

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [
            os.path.join(MRV2_ROOT_DIR, "hooks")
        ]

    def get_workfile_extensions(self):
        return [".mrv2s"]
