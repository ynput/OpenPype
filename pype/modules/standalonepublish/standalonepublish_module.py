import os
import sys
import subprocess
import pype
from .. import PypeModule, ITrayModule, IPluginPaths


class StandAlonePublishModule(PypeModule, ITrayModule):
    menu_label = "Publish"
    name = "Standalone Publish"

    def initialize(self, modules_settings):
        self.enabled = modules_settings[self.name]["enabled"]
        self.publish_paths = [
            os.path.join(
                pype.PLUGINS_DIR, "standalonepublisher", "publish"
            )
        ]

    def tray_init(self):
        return

    def tray_start(self):
        return

    def tray_exit(self):
        return

    def tray_menu(self, parent_menu):
        from Qt import QtWidgets
        run_action = QtWidgets.QAction(self.menu_label, parent_menu)
        run_action.triggered.connect(self.run_standalone_publisher)
        parent_menu.addAction(run_action)

    def connect_with_modules(self, enabled_modules):
        """Collect publish paths from other modules."""
        for module in enabled_modules:
            if isinstance(module, IPluginPaths):
                plugin_paths = module.get_plugin_paths() or {}
                publish_paths = plugin_paths.get("publish") or []
                if not isinstance(publish_paths, (list, tuple, set)):
                    publish_paths = [publish_paths]
                self.publish_paths.extend(publish_paths)

    def run_standalone_publisher(self):
        from pype import tools
        standalone_publisher_tool_path = os.path.join(
            os.path.dirname(os.path.abspath(tools.__file__)),
            "standalonepublish"
        )
        subprocess.Popen([
            sys.executable,
            standalone_publisher_tool_path,
            os.pathsep.join(self.publish_paths).replace("\\", "/")
        ])
