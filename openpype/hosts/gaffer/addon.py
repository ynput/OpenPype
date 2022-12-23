import os
from openpype.modules import OpenPypeModule, IHostAddon

GAFFER_HOST_DIR = os.path.dirname(os.path.abspath(__file__))


class GafferAddon(OpenPypeModule, IHostAddon):
    name = "gaffer"
    host_name = "gaffer"

    def initialize(self, module_settings):
        self.enabled = True

    def add_implementation_envs(self, env, _app):
        # Add requirements to GAFFER_STARTUP_PATHS
        startup_path = os.path.join(GAFFER_HOST_DIR, "startup")
        if env.get("GAFFER_STARTUP_PATHS"):
            startup_path += os.pathsep + env["GAFFER_STARTUP_PATHS"]

        env["GAFFER_STARTUP_PATHS"] = startup_path

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [
            os.path.join(GAFFER_HOST_DIR, "hooks")
        ]

    def get_workfile_extensions(self):
        return [".gfr"]
