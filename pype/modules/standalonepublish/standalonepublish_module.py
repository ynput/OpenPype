import os
import sys
import subprocess
import pype
from pype import tools


class StandAlonePublishModule:
    def __init__(self, main_parent=None, parent=None):
        self.main_parent = main_parent
        self.parent_widget = parent
        self.publish_paths = [
            os.path.join(
                pype.PLUGINS_DIR, "standalonepublisher", "publish"
            )
        ]

    def tray_menu(self, parent_menu):
        from Qt import QtWidgets
        self.run_action = QtWidgets.QAction(
            "Publish", parent_menu
        )
        self.run_action.triggered.connect(self.show)
        parent_menu.addAction(self.run_action)

    def process_modules(self, modules):
        if "FtrackModule" in modules:
            self.publish_paths.append(os.path.join(
                pype.PLUGINS_DIR, "ftrack", "publish"
            ))

    def show(self):
        standalone_publisher_tool_path = os.path.join(
            os.path.dirname(tools.__file__),
            "standalonepublish"
        )
        subprocess.Popen([
            sys.executable,
            standalone_publisher_tool_path,
            os.pathsep.join(self.publish_paths).replace("\\", "/")
        ])
