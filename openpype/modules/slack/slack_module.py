import os
from openpype.modules import (
    PypeModule, IPluginPaths)


class SlackIntegrationModule(PypeModule, IPluginPaths):
    """Allows sending notification to Slack channels during publishing."""

    name = "slack"

    def initialize(self, modules_settings):
        slack_settings = modules_settings[self.name]
        self.enabled = slack_settings["enabled"]

    def connect_with_modules(self, _enabled_modules):
        """Nothing special."""
        return

    def get_plugin_paths(self):
        """Deadline plugin paths."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return {
            "publish": [os.path.join(current_dir, "plugins", "publish")]
        }


