import os
from openpype.modules import OpenPypeModule, IHostAddon

SUBSTANCE_HOST_DIR = os.path.dirname(os.path.abspath(__file__))


class SubstanceAddon(OpenPypeModule, IHostAddon):
    name = "substancepainter"
    host_name = "substancepainter"

    def initialize(self, module_settings):
        self.enabled = True

    def add_implementation_envs(self, env, _app):
        # Add requirements to SUBSTANCE_PAINTER_PLUGINS_PATH
        plugin_path = os.path.join(SUBSTANCE_HOST_DIR, "deploy")
        plugin_path = plugin_path.replace("\\", "/")
        if env.get("SUBSTANCE_PAINTER_PLUGINS_PATH"):
            plugin_path += os.pathsep + env["SUBSTANCE_PAINTER_PLUGINS_PATH"]

        env["SUBSTANCE_PAINTER_PLUGINS_PATH"] = plugin_path

        # Log in Substance Painter doesn't support custom terminal colors
        env["OPENPYPE_LOG_NO_COLORS"] = "Yes"

    def get_launch_hook_paths(self, app):
        if app.host_name != self.host_name:
            return []
        return [
            os.path.join(SUBSTANCE_HOST_DIR, "hooks")
        ]

    def get_workfile_extensions(self):
        return [".spp", ".toc"]
