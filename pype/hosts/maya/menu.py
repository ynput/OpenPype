import sys
import os
import logging

from avalon.vendor.Qt import QtWidgets, QtGui
from avalon.maya import pipeline
from ...lib import BuildWorkfile
import maya.cmds as cmds

self = sys.modules[__name__]
self._menu = os.environ['PYPE_STUDIO_NAME']

log = logging.getLogger(__name__)


def _get_menu():
    """Return the menu instance if it currently exists in Maya"""

    widgets = dict((
        w.objectName(), w) for w in QtWidgets.QApplication.allWidgets())
    menu = widgets.get(self._menu)
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

    log.info("Attempting to install scripts menu..")

    try:
        import scriptsmenu.launchformaya as launchformaya
        import scriptsmenu.scriptsmenu as scriptsmenu
    except ImportError:
        log.warning(
            "Skipping studio.menu install, because "
            "'scriptsmenu' module seems unavailable."
        )
        add_build_workfiles_item()
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
        log.info("Skipping pype.menu initialization in batch mode..")
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
