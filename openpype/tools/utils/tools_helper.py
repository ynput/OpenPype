from avalon import api
from Qt import QtCore


class AvalonToolsHelper:
    def __init__(self):
        self._workfiles_tool = None
        self._loader_tool = None
        self._creator_tool = None
        self._subset_manager_tool = None
        self._scene_inventory_tool = None
        self._library_loader_tool = None

    def workfiles_tool(self):
        if self._workfiles_tool is not None:
            return self._workfiles_tool

        from openpype.tools.workfiles.app import (
            Window, validate_host_requirements
        )
        # Host validation
        host = api.registered_host()
        validate_host_requirements(host)

        window = Window()
        window.refresh()
        window.setWindowFlags(
            window.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
        )

        # window.setStyleSheet(style.load_stylesheet())

        context = {
            "asset": api.Session["AVALON_ASSET"],
            "silo": api.Session["AVALON_SILO"],
            "task": api.Session["AVALON_TASK"]
        }
        window.set_context(context)

        self._workfiles_tool = window

        return window

    def show_workfiles_tool(self):
        workfiles_tool = self.workfiles_tool()
        workfiles_tool.refresh()
        workfiles_tool.show()
        # Pull window to the front.
        workfiles_tool.raise_()
        workfiles_tool.activateWindow()

    def loader_tool(self):
        if self._loader_tool is not None:
            return self._loader_tool

        from openpype.tools.loader import LoaderWindow

        window = LoaderWindow()
        window.setWindowFlags(
            window.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
        )

        context = {"asset": api.Session["AVALON_ASSET"]}
        window.set_context(context, refresh=True)

        self._loader_tool = window

        return window

    def show_loader_tool(self):
        loader_tool = self.loader_tool()
        loader_tool.show()
        loader_tool.raise_()
        loader_tool.activateWindow()
        loader_tool.refresh()

    def creator_tool(self):
        if self._creator_tool is not None:
            return self._creator_tool

        from avalon.tools.creator.app import Window
        window = Window()
        window.setWindowFlags(
            window.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
        )

        self._creator_tool = window

        return window

    def show_creator_tool(self):
        creator_tool = self.creator_tool()
        creator_tool.refresh()
        creator_tool.show()

        # Pull window to the front.
        creator_tool.raise_()
        creator_tool.activateWindow()

    def subset_manager_tool(self):
        if self._subset_manager_tool is not None:
            return self._subset_manager_tool

        from avalon.tools.subsetmanager import Window
        # from ..tools.sceneinventory.app import Window
        window = Window()
        window.setWindowFlags(
            window.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
        )

        self._subset_manager_tool = window

        return window

    def show_subset_manager_tool(self):
        subset_manager_tool = self.subset_manager_tool()
        subset_manager_tool.show()

        # Pull window to the front.
        subset_manager_tool.raise_()
        subset_manager_tool.activateWindow()

    def scene_inventory_tool(self):
        if self._scene_inventory_tool is not None:
            return self._scene_inventory_tool

        from avalon.tools.sceneinventory.app import Window
        window = Window()
        window.setWindowFlags(
            window.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
        )

        self._scene_inventory_tool = window

        return window

    def show_scene_inventory_tool(self):
        scene_inventory_tool = self.scene_inventory_tool()
        scene_inventory_tool.show()
        scene_inventory_tool.refresh()

        # Pull window to the front.
        scene_inventory_tool.raise_()
        scene_inventory_tool.activateWindow()

    def library_loader_tool(self):
        if self._library_loader_tool is not None:
            return self._library_loader_tool

        from openpype.tools.libraryloader import LibraryLoaderWindow

        window = LibraryLoaderWindow()
        window.setWindowFlags(
            window.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
        )

        self._library_loader_tool = window

        return window

    def show_library_loader_tool(self):
        library_loader_tool = self.library_loader_tool()
        library_loader_tool.show()
        library_loader_tool.raise_()
        library_loader_tool.activateWindow()
        library_loader_tool.refresh()
