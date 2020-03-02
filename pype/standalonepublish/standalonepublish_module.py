import os
from .app import show
from .widgets import QtWidgets
import pype
from . import PUBLISH_PATHS


class StandAlonePublishModule:

    def __init__(self, main_parent=None, parent=None):
        self.main_parent = main_parent
        self.parent_widget = parent
        PUBLISH_PATHS.clear()
        PUBLISH_PATHS.append(os.path.sep.join(
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
            PUBLISH_PATHS.append(os.path.sep.join(
                [pype.PLUGINS_DIR, "ftrack", "publish"]
            ))

    def show(self):
        show(self.main_parent, False)
