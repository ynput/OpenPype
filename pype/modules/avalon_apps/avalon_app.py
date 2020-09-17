from Qt import QtWidgets
from avalon.tools import libraryloader
from pype.api import Logger
from pype.tools.launcher import LauncherWindow, actions


class AvalonApps:
    def __init__(self, main_parent=None, parent=None):
        self.log = Logger().get_logger(__name__)
        self.main_parent = main_parent
        self.parent = parent

        self.app_launcher = LauncherWindow()

        # actions.register_default_actions()
        actions.register_config_actions()
        actions.register_environment_actions()

    def process_modules(self, modules):
        if "RestApiServer" in modules:
            from .rest_api import AvalonRestApi
            self.rest_api_obj = AvalonRestApi()

    # Definition of Tray menu
    def tray_menu(self, parent_menu=None):
        # Actions
        if parent_menu is None:
            if self.parent is None:
                self.log.warning('Parent menu is not set')
                return
            elif self.parent.hasattr('menu'):
                parent_menu = self.parent.menu
            else:
                self.log.warning('Parent menu is not set')
                return

        action_launcher = QtWidgets.QAction("Launcher", parent_menu)
        action_library_loader = QtWidgets.QAction(
            "Library loader", parent_menu
        )

        action_launcher.triggered.connect(self.show_launcher)
        action_library_loader.triggered.connect(self.show_library_loader)

        parent_menu.addAction(action_launcher)
        parent_menu.addAction(action_library_loader)

    def show_launcher(self):
        # if app_launcher don't exist create it/otherwise only show main window
        self.app_launcher.show()
        self.app_launcher.raise_()
        self.app_launcher.activateWindow()

    def show_library_loader(self):
        libraryloader.show(
            parent=self.main_parent,
            icon=self.parent.icon,
            show_projects=True,
            show_libraries=True
        )
