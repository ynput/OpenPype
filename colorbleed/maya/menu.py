import sys
import os
import logging
import site

from avalon.vendor.Qt import QtWidgets, QtCore

import maya.cmds as cmds

self = sys.modules[__name__]
self._menu = "colorbleed"

# set colorbleed scripts path in environment keys
os.environ["COLORBLEED_SCRIPTS"] = r"P:\pipeline\dev\git\cbMayaScripts\cbMayaScripts"

log = logging.getLogger(__name__)


def deferred():

    # todo: replace path with server / library path
    site.addsitedir("C:\Users\User\Documents\development\scriptsmenu\python")

    from scriptsmenu import launchformaya
    import scriptsmenu.scriptsmenu as menu

    log.info("Attempting to install ...")

    # load configuration of custom menu
    config_path = os.path.join(os.path.dirname(__file__), "menu.json")
    config = menu.load_configuration(config_path)

    # get Maya menubar
    parent = launchformaya._maya_main_menubar()
    cb_menu = menu.ScriptsMenu(objectName=self._menu,
                               title=self._menu.title(),
                               parent=parent)

    # register modifiers
    modifiers = QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier
    cb_menu.register_callback(modifiers, launchformaya.to_shelf)

    # apply configuration
    menu.load_from_configuration(cb_menu, config)


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
