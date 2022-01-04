import os
import openpype
from openpype.modules import OpenPypeModule
from openpype_interfaces import ITrayModule


class AvalonModule(OpenPypeModule, ITrayModule):
    name = "avalon"

    def initialize(self, modules_settings):
        # This module is always enabled
        self.enabled = True

        avalon_settings = modules_settings[self.name]

        thumbnail_root = os.environ.get("AVALON_THUMBNAIL_ROOT")
        if not thumbnail_root:
            thumbnail_root = avalon_settings["AVALON_THUMBNAIL_ROOT"]

        # Mongo timeout
        avalon_mongo_timeout = os.environ.get("AVALON_TIMEOUT")
        if not avalon_mongo_timeout:
            avalon_mongo_timeout = avalon_settings["AVALON_TIMEOUT"]

        self.thumbnail_root = thumbnail_root
        self.avalon_mongo_timeout = avalon_mongo_timeout

        # Tray attributes
        self.libraryloader = None
        self.rest_api_obj = None

    def get_global_environments(self):
        """Avalon global environments for pype implementation."""
        return {
            # TODO thumbnails root should be multiplafrom
            # - thumbnails root
            "AVALON_THUMBNAIL_ROOT": self.thumbnail_root,
            # - mongo timeout in ms
            "AVALON_TIMEOUT": str(self.avalon_mongo_timeout),
        }

    def tray_init(self):
        # Add library tool
        try:
            from openpype.tools.libraryloader import LibraryLoaderWindow

            self.libraryloader = LibraryLoaderWindow(
                show_projects=True,
                show_libraries=True
            )
        except Exception:
            self.log.warning(
                "Couldn't load Library loader tool for tray.",
                exc_info=True
            )

    # Definition of Tray menu
    def tray_menu(self, tray_menu):
        if self.libraryloader is None:
            return

        from Qt import QtWidgets
        # Actions
        action_library_loader = QtWidgets.QAction(
            "Loader", tray_menu
        )

        action_library_loader.triggered.connect(self.show_library_loader)

        tray_menu.addAction(action_library_loader)

    def tray_start(self, *_a, **_kw):
        return

    def tray_exit(self, *_a, **_kw):
        return

    def show_library_loader(self):
        if self.libraryloader is None:
            return

        self.libraryloader.show()

        # Raise and activate the window
        # for MacOS
        self.libraryloader.raise_()
        # for Windows
        self.libraryloader.activateWindow()
        self.libraryloader.refresh()

    # Webserver module implementation
    def webserver_initialization(self, server_manager):
        """Add routes for webserver."""
        if self.tray_initialized:
            from .rest_api import AvalonRestApiResource
            self.rest_api_obj = AvalonRestApiResource(self, server_manager)
