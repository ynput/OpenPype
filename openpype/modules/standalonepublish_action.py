import os
import platform
import subprocess
from openpype.lib import get_openpype_execute_args
from openpype.modules import OpenPypeModule
from openpype_interfaces import ITrayAction


class StandAlonePublishAction(OpenPypeModule, ITrayAction):
    label = "Publish"
    name = "standalonepublish_tool"

    def initialize(self, modules_settings):
        import openpype
        self.enabled = modules_settings[self.name]["enabled"]
        self.publish_paths = [
            os.path.join(
                openpype.PACKAGE_DIR,
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
        args = get_openpype_execute_args("standalonepublisher")
        kwargs = {}
        if platform.system().lower() == "darwin":
            new_args = ["open", "-na", args.pop(0), "--args"]
            new_args.extend(args)
            args = new_args

        detached_process = getattr(subprocess, "DETACHED_PROCESS", None)
        if detached_process is not None:
            kwargs["creationflags"] = detached_process

        subprocess.Popen(args, **kwargs)
