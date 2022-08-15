import os
from openpype.lib import get_openpype_execute_args
from openpype.lib.execute import run_detached_process
from openpype.modules import OpenPypeModule
from openpype.modules.interfaces import ITrayAction


class TrayPublishAction(OpenPypeModule, ITrayAction):
    label = "New Publish (beta)"
    name = "traypublish_tool"

    def initialize(self, modules_settings):
        import openpype
        self.enabled = True
        self.publish_paths = [
            os.path.join(
                openpype.PACKAGE_DIR,
                "hosts",
                "traypublisher",
                "plugins",
                "publish"
            )
        ]

    def tray_init(self):
        return

    def on_action_trigger(self):
        self.run_traypublisher()

    def connect_with_modules(self, enabled_modules):
        """Collect publish paths from other modules."""
        publish_paths = self.manager.collect_plugin_paths()["publish"]
        self.publish_paths.extend(publish_paths)

    def run_traypublisher(self):
        args = get_openpype_execute_args("traypublisher")
        run_detached_process(args)
