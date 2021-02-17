import os
import sys
import subprocess
from pype.lib import get_pype_execute_args
from . import PypeModule, ITrayAction


class StandAlonePublishAction(PypeModule, ITrayAction):
    label = "Publish"
    name = "standalonepublish_tool"

    def initialize(self, modules_settings):
        import pype
        self.enabled = modules_settings[self.name]["enabled"]
        self.publish_paths = [
            os.path.join(
                pype.PACKAGE_DIR,
                "hosts",
                "standalonepublisher",
                "plugins",
                "publish"
            )
        ]

    def tray_init(self):
        return

    def on_action_trigger(self):
        self.run_standalone_publisher()

    def connect_with_modules(self, enabled_modules):
        """Collect publish paths from other modules."""
        publish_paths = self.manager.collect_plugin_paths()["publish"]
        self.publish_paths.extend(publish_paths)

    def run_standalone_publisher(self):
        args = get_pype_execute_args("standalonepublisher")
        subprocess.Popen(args, creationflags=subprocess.DETACHED_PROCESS)
