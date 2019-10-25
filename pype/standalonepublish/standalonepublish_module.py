import os
from .app import show
from .widgets import QtWidgets
import pype
import pyblish.api


class StandAlonePublishModule:
    PUBLISH_PATHS = []

    def __init__(self, main_parent=None, parent=None):
        self.main_parent = main_parent
        self.parent_widget = parent
        self.PUBLISH_PATHS.append(os.path.sep.join(
            [pype.PLUGINS_DIR, "standalonepublisher", "publish"]
        ))

    def tray_menu(self, parent_menu):
        self.run_action = QtWidgets.QAction(
            "Publish", parent_menu
        )
        self.run_action.triggered.connect(self.show)
        parent_menu.addAction(self.run_action)

    def process_modules(self, modules):
        if "FtrackModule" in modules:
            self.PUBLISH_PATHS.append(os.path.sep.join(
                [pype.PLUGINS_DIR, "ftrack", "publish"]
            ))

    def tray_start(self):
        # Registers Global pyblish plugins
        pype.install()
        # Registers Standalone pyblish plugins
        for path in self.PUBLISH_PATHS:
            pyblish.api.register_plugin_path(path)

    def show(self):
        show(self.main_parent, False)
