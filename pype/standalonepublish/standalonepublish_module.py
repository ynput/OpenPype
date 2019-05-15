from .app import show
from .widgets import QtWidgets


class StandAlonePublishModule:
    def __init__(self, main_parent=None, parent=None):
        self.main_parent = main_parent
        self.parent_widget = parent

    def tray_menu(self, parent_menu):
        self.run_action = QtWidgets.QAction(
            "Publish", parent_menu
        )
        self.run_action.triggered.connect(self.show)
        parent_menu.addAction(self.run_action)

    def show(self):
        show(self.main_parent, False)
