import os
import argparse
from Qt import QtGui, QtWidgets
from avalon.tools import libraryloader
from pype.api import Logger
from avalon import io
from launcher import launcher_widget, lib as launcher_lib


class AvalonApps:
    def __init__(self, main_parent=None, parent=None):
        self.log = Logger().get_logger(__name__)
        self.main_parent = main_parent
        self.parent = parent
        self.app_launcher = None

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

        icon = QtGui.QIcon(launcher_lib.resource("icon", "main.png"))
        aShowLauncher = QtWidgets.QAction(icon, "&Launcher", parent_menu)
        aLibraryLoader = QtWidgets.QAction("Library", parent_menu)

        aShowLauncher.triggered.connect(self.show_launcher)
        aLibraryLoader.triggered.connect(self.show_library_loader)

        parent_menu.addAction(aShowLauncher)
        parent_menu.addAction(aLibraryLoader)

    def show_launcher(self):
        # if app_launcher don't exist create it/otherwise only show main window
        if self.app_launcher is None:
            io.install()
            APP_PATH = launcher_lib.resource("qml", "main.qml")
            self.app_launcher = launcher_widget.Launcher(APP_PATH)
        self.app_launcher.window.show()

    def show_library_loader(self):
        libraryloader.show(
            parent=self.main_parent,
            icon=self.parent.icon,
            show_projects=True,
            show_libraries=True
        )
