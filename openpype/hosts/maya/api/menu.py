import sys
import os
import logging

from avalon.vendor.Qt import QtWidgets, QtGui
from avalon.maya import pipeline
from openpype.api import BuildWorkfile
import maya.cmds as cmds

self = sys.modules[__name__]
self._menu = os.environ.get("AVALON_LABEL")


log = logging.getLogger(__name__)


def _get_menu(menu_name=None):
    """Return the menu instance if it currently exists in Maya"""

    if menu_name is None:
        menu_name = self._menu
    widgets = dict((
        w.objectName(), w) for w in QtWidgets.QApplication.allWidgets())
    menu = widgets.get(menu_name)
    return menu


def deferred():
    def add_build_workfiles_item():
        # Add build first workfile
        cmds.menuItem(divider=True, parent=pipeline._menu)
        cmds.menuItem(
            "Build First Workfile",
            parent=pipeline._menu,
            command=lambda *args: BuildWorkfile().process()
        )

    def add_look_assigner_item():
        import mayalookassigner
        cmds.menuItem(
            "Look assigner",
            parent=pipeline._menu,
            command=lambda *args: mayalookassigner.show()
        )

    def modify_workfiles():
        from openpype.tools import workfiles

        def launch_workfiles_app(*_args, **_kwargs):
            workfiles.show(
                os.path.join(
                    cmds.workspace(query=True, rootDirectory=True),
                    cmds.workspace(fileRuleEntry="scene")
                ),
                parent=pipeline._parent
            )

        # Find the pipeline menu
        top_menu = _get_menu(pipeline._menu)

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
            command=launch_workfiles_app,
            insertAfter=after_action
        )

        # Remove replaced action
        if workfile_action:
            top_menu.removeAction(workfile_action)

    log.info("Attempting to install scripts menu..")

    add_build_workfiles_item()
    add_look_assigner_item()
    modify_workfiles()

    try:
        import scriptsmenu.launchformaya as launchformaya
        import scriptsmenu.scriptsmenu as scriptsmenu
    except ImportError:
        log.warning(
            "Skipping studio.menu install, because "
            "'scriptsmenu' module seems unavailable."
        )
        return

    # load configuration of custom menu
    config_path = os.path.join(os.path.dirname(__file__), "menu.json")
    config = scriptsmenu.load_configuration(config_path)

    # run the launcher for Maya menu
    studio_menu = launchformaya.main(
        title=self._menu.title(),
        objectName=self._menu
    )

    # apply configuration
    studio_menu.build_from_configuration(studio_menu, config)


def uninstall():
    menu = _get_menu()
    if menu:
        log.info("Attempting to uninstall..")

        try:
            menu.deleteLater()
            del menu
        except Exception as e:
            log.error(e)


def install():
    if cmds.about(batch=True):
        log.info("Skipping openpype.menu initialization in batch mode..")
        return

    uninstall()
    # Allow time for uninstallation to finish.
    cmds.evalDeferred(deferred)


def popup():
    """Pop-up the existing menu near the mouse cursor"""
    menu = _get_menu()

    cursor = QtGui.QCursor()
    point = cursor.pos()
    menu.exec_(point)
