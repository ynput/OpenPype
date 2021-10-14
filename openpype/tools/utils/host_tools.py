"""Single access point to all tools usable in hosts.

It is possible to create `HostToolsHelper` in host implementaion or
use singleton approach with global functions (using helper anyway).
"""

from Qt import QtCore
import avalon.api


class HostToolsHelper:
    """Create and cache tool windows in memory.

    Almost all methods expect parent widget but the parent is used only on
    first tool creation.

    Class may also contain tools that are available only for one or few hosts.
    """
    def __init__(self, parent=None):
        self._parent = parent
        self._workfiles_tool = None
        self._loader_tool = None
        self._creator_tool = None
        self._subset_manager_tool = None
        self._scene_inventory_tool = None
        self._library_loader_tool = None

    def _get_workfiles_tool(self, parent):
        if self._workfiles_tool is None:
            from openpype.tools.workfiles.app import (
                Window, validate_host_requirements
            )
            # Host validation
            host = avalon.api.registered_host()
            validate_host_requirements(host)

            window = Window(parent=parent)

            context = {
                "asset": avalon.api.Session["AVALON_ASSET"],
                "silo": avalon.api.Session["AVALON_SILO"],
                "task": avalon.api.Session["AVALON_TASK"]
            }
            window.set_context(context)

            self._workfiles_tool = window

        return self._workfiles_tool

    def show_workfiles_tool(self, parent=None):
        workfiles_tool = self._get_workfiles_tool(parent)

        workfiles_tool.refresh()
        workfiles_tool.show()
        # Pull window to the front.
        workfiles_tool.raise_()
        workfiles_tool.activateWindow()

    def _get_loader_tool(self, parent):
        if self._loader_tool is None:
            from openpype.tools.loader import LoaderWindow

            self._loader_tool = LoaderWindow(parent=parent or self._parent)

        return self._loader_tool

    def show_loader_tool(self, parent=None):
        loader_tool = self._get_loader_tool(parent)

        context = {"asset": avalon.api.Session["AVALON_ASSET"]}
        loader_tool.set_context(context, refresh=True)

        loader_tool.show()
        loader_tool.raise_()
        loader_tool.activateWindow()
        loader_tool.refresh()

    def _get_creator_tool(self, parent):
        if self._creator_tool is None:
            from avalon.tools.creator.app import Window

            self._creator_tool = Window(parent=parent or self._parent)

        return self._creator_tool

    def show_creator_tool(self, parent=None):
        creator_tool = self._get_creator_tool(parent)
        creator_tool.refresh()
        creator_tool.show()

        # Pull window to the front.
        creator_tool.raise_()
        creator_tool.activateWindow()

    def _get_subset_manager_tool(self, parent):
        if self._subset_manager_tool is None:
            from avalon.tools.subsetmanager import Window

            self._subset_manager_tool = Window(parent=parent or self._parent)

        return self._subset_manager_tool

    def show_subset_manager_tool(self, parent=None):
        subset_manager_tool = self._get_subset_manager_tool(parent)
        subset_manager_tool.show()

        # Pull window to the front.
        subset_manager_tool.raise_()
        subset_manager_tool.activateWindow()

    def _get_scene_inventory_tool(self, parent):
        if self._scene_inventory_tool is None:
            from avalon.tools.sceneinventory.app import Window

            self._scene_inventory_tool = Window(parent=parent or self._parent)

        return self._scene_inventory_tool

    def show_scene_inventory_tool(self, parent=None):
        scene_inventory_tool = self._get_scene_inventory_tool(parent)
        scene_inventory_tool.show()
        scene_inventory_tool.refresh()

        # Pull window to the front.
        scene_inventory_tool.raise_()
        scene_inventory_tool.activateWindow()

    def _get_library_loader_tool(self, parent):
        if self._library_loader_tool is None:
            from openpype.tools.libraryloader import LibraryLoaderWindow

            self._library_loader_tool = LibraryLoaderWindow(
                parent=parent or self._parent
            )

        return self._library_loader_tool

    def show_library_loader_tool(self, parent=None):
        library_loader_tool = self._get_library_loader_tool(parent)
        library_loader_tool.show()
        library_loader_tool.raise_()
        library_loader_tool.activateWindow()
        library_loader_tool.refresh()

    def show_publish_tool(self, parent=None):
        from avalon.tools import publish

        publish.show(parent)

    def show_tool_by_name(self, tool_name, parent=None):
        if tool_name == "workfiles":
            self.show_workfiles_tool(parent)

        elif tool_name == "loader":
            self.show_loader_tool(parent)

        elif tool_name == "libraryloader":
            self.show_library_loader_tool(parent)

        elif tool_name == "creator":
            self.show_creator_tool(parent)

        elif tool_name == "subset_manager":
            self.show_subset_manager_tool(parent)

        elif tool_name == "scene_inventory":
            self.show_scene_inventory_tool(parent)


class _SingletonPoint:
    helper = None

    @classmethod
    def _create_helper(cls):
        if cls.helper is None:
            cls.helper = HostToolsHelper()

    @classmethod
    def show_tool_by_name(cls, tool_name, parent=None):
        cls._create_helper()
        cls.helper.show_tool_by_name(tool_name, parent)


def show_workfiles_tool(parent=None):
    _SingletonPoint.show_tool_by_name("workfiles", parent)


def show_loader_tool(parent=None):
    _SingletonPoint.show_tool_by_name("loader", parent)


def show_library_loader_tool(parent=None):
    _SingletonPoint.show_tool_by_name("libraryloader", parent)


def show_creator_tool(parent=None):
    _SingletonPoint.show_tool_by_name("creator", parent)


def show_subset_manager_tool(parent=None):
    _SingletonPoint.show_tool_by_name("subset_manager", parent)


def show_scene_inventory_tool(parent=None):
    _SingletonPoint.show_tool_by_name("scene_inventory", parent)
