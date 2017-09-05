import sys
import os
import logging

from avalon.vendor.Qt import QtWidgets, QtCore

import maya.cmds as cmds

self = sys.modules[__name__]
self._menu = "colorbleed"

log = logging.getLogger(__name__)


def deferred():

    import scriptsmenu.launchformaya as launchformaya
    import scriptsmenu.scriptsmenu as scriptsmenu

    log.info("Attempting to install ...")

    # load configuration of custom menu
    config_path = os.path.join(os.path.dirname(__file__), "menu.json")
    config = scriptsmenu.load_configuration(config_path)

    # run the launcher for Maya menu
    cb_menu = launchformaya.main(title=self._menu.title(),
                                 objectName=self._menu)

    # register modifiers
    modifiers = QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier
    cb_menu.register_callback(modifiers, launchformaya.to_shelf)

    # apply configuration
    cb_menu.build_from_configuration(cb_menu, config)


def uninstall():

    log.info("Attempting to uninstall ..")
    app = QtWidgets.QApplication.instance()
    widgets = dict((w.objectName(), w) for w in app.allWidgets())
    menu = widgets.get(self._menu)

    if menu:
        try:
            menu.deleteLater()
            del menu
        except Exception as e:
            log.error(e)


def install():

    uninstall()
    # Allow time for uninstallation to finish.
    cmds.evalDeferred(deferred)
