import sys
import os
import logging

from Qt import QtWidgets, QtGui

import maya.cmds as cmds

from avalon.maya import pipeline

from openpype.api import BuildWorkfile
from openpype.api import BuildWorkfileTemplate
import maya.cmds as cmds
from openpype.settings import get_project_settings
from openpype.tools.utils import host_tools
from openpype.hosts.maya.api import lib


log = logging.getLogger(__name__)


def _get_menu(menu_name=None):
    """Return the menu instance if it currently exists in Maya"""
    if menu_name is None:
        menu_name = pipeline._menu

    widgets = {w.objectName(): w for w in QtWidgets.QApplication.allWidgets()}
    return widgets.get(menu_name)


def deferred():
    def add_build_workfiles_item():
        # Add build first workfile
        cmds.menuItem(divider=True, parent=pipeline._menu)
        cmds.menuItem(
            "Build First Workfile",
            parent=pipeline._menu,
            command=lambda *args: BuildWorkfileTemplate().process()
        )

    def add_look_assigner_item():
        cmds.menuItem(
            "Look assigner",
            parent=pipeline._menu,
            command=lambda *args: host_tools.show_look_assigner(
                pipeline._parent
            )
        )

    def add_experimental_item():
        cmds.menuItem(
            "Experimental tools...",
            parent=pipeline._menu,
            command=lambda *args: host_tools.show_experimental_tools_dialog(
                pipeline._parent
            )
        )

    def add_scripts_menu():
        try:
            import scriptsmenu.launchformaya as launchformaya
        except ImportError:
            log.warning(
                "Skipping studio.menu install, because "
                "'scriptsmenu' module seems unavailable."
            )
            return

        # load configuration of custom menu
        project_settings = get_project_settings(os.getenv("AVALON_PROJECT"))
        config = project_settings["maya"]["scriptsmenu"]["definition"]
        _menu = project_settings["maya"]["scriptsmenu"]["name"]

        if not config:
            log.warning("Skipping studio menu, no definition found.")
            return

        # run the launcher for Maya menu
        studio_menu = launchformaya.main(
            title=_menu.title(),
            objectName=_menu.title().lower().replace(" ", "_")
        )

        # apply configuration
        studio_menu.build_from_configuration(studio_menu, config)

    def modify_workfiles():
        # Find the pipeline menu
        top_menu = _get_menu()

        # Try to find workfile tool action in the menu
        workfile_action = None
        for action in top_menu.actions():
            if action.text() == "Work Files":
                workfile_action = action
                break

        # Add at the top of menu if "Work Files" action was not found
        after_action = ""
        if workfile_action:
            # Use action's object name for `insertAfter` argument
            after_action = workfile_action.objectName()

        # Insert action to menu
        cmds.menuItem(
            "Work Files",
            parent=pipeline._menu,
            command=lambda *args: host_tools.show_workfiles(pipeline._parent),
            insertAfter=after_action
        )

        # Remove replaced action
        if workfile_action:
            top_menu.removeAction(workfile_action)

    def modify_resolution():
        # Find the pipeline menu
        top_menu = _get_menu()

        # Try to find resolution tool action in the menu
        resolution_action = None
        for action in top_menu.actions():
            if action.text() == "Reset Resolution":
                resolution_action = action
                break

        # Add at the top of menu if "Work Files" action was not found
        after_action = ""
        if resolution_action:
            # Use action's object name for `insertAfter` argument
            after_action = resolution_action.objectName()

        # Insert action to menu
        cmds.menuItem(
            "Reset Resolution",
            parent=pipeline._menu,
            command=lambda *args: lib.reset_scene_resolution(),
            insertAfter=after_action
        )

        # Remove replaced action
        if resolution_action:
            top_menu.removeAction(resolution_action)

    def remove_project_manager():
        top_menu = _get_menu()

        # Try to find "System" menu action in the menu
        system_menu = None
        for action in top_menu.actions():
            if action.text() == "System":
                system_menu = action
                break

        if system_menu is None:
            return

        # Try to find "Project manager" action in "System" menu
        project_manager_action = None
        for action in system_menu.menu().children():
            if hasattr(action, "text") and action.text() == "Project Manager":
                project_manager_action = action
                break

        # Remove "Project manager" action if was found
        if project_manager_action is not None:
            system_menu.menu().removeAction(project_manager_action)

    def add_colorspace():
        # Find the pipeline menu
        top_menu = _get_menu()

        # Try to find workfile tool action in the menu
        workfile_action = None
        for action in top_menu.actions():
            if action.text() == "Reset Resolution":
                workfile_action = action
                break

        # Add at the top of menu if "Work Files" action was not found
        after_action = ""
        if workfile_action:
            # Use action's object name for `insertAfter` argument
            after_action = workfile_action.objectName()

        # Insert action to menu
        cmds.menuItem(
            "Set Colorspace",
            parent=pipeline._menu,
            command=lambda *args: lib.set_colorspace(),
            insertAfter=after_action
        )

    log.info("Attempting to install scripts menu ...")

    # add_scripts_menu()
    add_build_workfiles_item()
    add_look_assigner_item()
    add_experimental_item()
    modify_workfiles()
    modify_resolution()
    remove_project_manager()
    add_colorspace()
    add_scripts_menu()


def uninstall():
    menu = _get_menu()
    if menu:
        log.info("Attempting to uninstall ...")

        try:
            menu.deleteLater()
            del menu
        except Exception as e:
            log.error(e)


def install():
    if cmds.about(batch=True):
        log.info("Skipping openpype.menu initialization in batch mode..")
        return

    # Allow time for uninstallation to finish.
    cmds.evalDeferred(deferred, lowestPriority=True)


def popup():
    """Pop-up the existing menu near the mouse cursor."""
    menu = _get_menu()
    cursor = QtGui.QCursor()
    point = cursor.pos()
    menu.exec_(point)
