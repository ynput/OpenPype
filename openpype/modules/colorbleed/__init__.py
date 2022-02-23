import os

from openpype.modules import OpenPypeModule
from openpype_interfaces import (
    ITrayModule,
    IPluginPaths
)


class ColorbleedModule(OpenPypeModule, IPluginPaths):
    name = "colorbleed"

    def initialize(self, modules_settings):
        self.enabled = True

    def get_plugin_paths(self):
        """Implementaton of IPluginPaths to get plugin paths."""
        actions_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "launcher_actions"
        )
        return {
            "actions": [actions_path]
        }
