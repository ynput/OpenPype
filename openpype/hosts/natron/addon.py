import os
from openpype.modules import OpenPypeModule, IHostAddon


NATRON_HOST_DIR = os.path.dirname(os.path.abspath(__file__))


class NatronAddon(OpenPypeModule, IHostAddon):
    name = "natron"
    host_name = "natron"

    def initialize(self, module_settings):
        self.enabled = True

    def add_implementation_envs(self, env, _app):
        # Add requirements to natron startup
        startup_path = os.path.join(NATRON_HOST_DIR, "startup")
        if env.get("NATRON_PLUGIN_PATH"):
            startup_path += os.pathsep + env["NATRON_PLUGIN_PATH"]

        env["NATRON_PLUGIN_PATH"] = startup_path

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [
            os.path.join(NATRON_HOST_DIR, "hooks")
        ]

    def get_workfile_extensions(self):
        return [".gfr"]
