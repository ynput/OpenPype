import os
import pype
from pype import resources
from .. import (
    PypeModule,
    ITrayModule,
    IWebServerRoutes
)


class AvalonModule(PypeModule, ITrayModule, IWebServerRoutes):
    name = "avalon"

    def initialize(self, modules_settings):
        # This module is always enabled
        self.enabled = True

        avalon_settings = modules_settings[self.name]

        # Check if environment is already set
        avalon_mongo_url = os.environ.get("AVALON_MONGO")
        if not avalon_mongo_url:
            avalon_mongo_url = avalon_settings["AVALON_MONGO"]
        # Use pype mongo if Avalon's mongo not defined
        if not avalon_mongo_url:
            avalon_mongo_url = os.environ["PYPE_MONGO"]

        thumbnail_root = os.environ.get("AVALON_THUMBNAIL_ROOT")
        if not thumbnail_root:
            thumbnail_root = avalon_settings["AVALON_THUMBNAIL_ROOT"]

        # Mongo timeout
        avalon_mongo_timeout = os.environ.get("AVALON_TIMEOUT")
        if not avalon_mongo_timeout:
            avalon_mongo_timeout = avalon_settings["AVALON_TIMEOUT"]

        self.thumbnail_root = thumbnail_root
        self.avalon_mongo_url = avalon_mongo_url
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
            from avalon.tools.libraryloader import app
            from avalon import style
            from Qt import QtGui

            self.libraryloader = app.Window(
                icon=QtGui.QIcon(resources.pype_icon_filepath()),
                show_projects=True,
                show_libraries=True
            )
            self.libraryloader.setStyleSheet(style.load_stylesheet())
        except Exception:
            self.log.warning(
                "Couldn't load Library loader tool for tray.",
                exc_info=True
            )

    def connect_with_modules(self, _enabled_modules):
        return

    def webserver_initialization(self, server_manager):
        """Implementation of IWebServerRoutes interface."""

        if self.tray_initialized:
            from .rest_api import AvalonRestApiResource
            self.rest_api_obj = AvalonRestApiResource(self, server_manager)

    # Definition of Tray menu
    def tray_menu(self, tray_menu):
        from Qt import QtWidgets
        # Actions
        action_library_loader = QtWidgets.QAction(
            "Library loader", tray_menu
        )

        action_library_loader.triggered.connect(self.show_library_loader)

        tray_menu.addAction(action_library_loader)

    def tray_start(self, *_a, **_kw):
        return

    def tray_exit(self, *_a, **_kw):
        return

    def show_library_loader(self):
        self.libraryloader.show()

        # Raise and activate the window
        # for MacOS
        self.libraryloader.raise_()
        # for Windows
        self.libraryloader.activateWindow()
        self.libraryloader.refresh()
