import sys
import os
import logging

from avalon.vendor.Qt import QtWidgets, QtGui
from avalon.maya import pipeline
from openpype.api import BuildWorkfile
import maya.cmds as cmds
from openpype.settings import get_project_settings

self = sys.modules[__name__]


log = logging.getLogger(__name__)


def _get_menu(menu_name=None):
    """Return the menu instance if it currently exists in Maya"""

    project_settings = get_project_settings(os.getenv("AVALON_PROJECT"))
    _menu = project_settings["maya"]["scriptsmenu"]["name"]

    if menu_name is None:
        menu_name = _menu
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

    log.info("Attempting to install scripts menu ...")

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

    uninstall()
    # Allow time for uninstallation to finish.
    cmds.evalDeferred(deferred)


def popup():
    """Pop-up the existing menu near the mouse cursor."""
    menu = _get_menu()
    cursor = QtGui.QCursor()
    point = cursor.pos()
    menu.exec_(point)
