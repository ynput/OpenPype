import os
import logging

import hou

from pyblish import api as pyblish

from avalon import api as avalon
from avalon.houdini import pipeline as houdini

from colorbleed.houdini import lib

from colorbleed.lib import (
    any_outdated,
    update_task_from_path
)


PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "houdini", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "houdini", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "houdini", "create")

log = logging.getLogger("colorbleed.houdini")


def install():

    # Set

    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)

    log.info("Installing callbacks ... ")
    avalon.on("init", on_init)
    avalon.on("save", on_save)
    avalon.on("open", on_open)

    log.info("Overriding existing event 'taskChanged'")

    log.info("Setting default family states for loader..")
    avalon.data["familiesStateToggled"] = ["colorbleed.imagesequence"]


def on_init(_):
    houdini.on_houdini_initialize()


def on_save(_):

    avalon.logger.info("Running callback on save..")

    update_task_from_path(hou.hipFile.path())

    nodes = lib.get_id_required_nodes()
    for node, new_id in lib.generate_ids(nodes):
        lib.set_id(node, new_id, overwrite=False)


def on_open():

    update_task_from_path(hou.hipFile.path())

    if any_outdated():
        from avalon.vendor.Qt import QtWidgets
        from ..widgets import popup

        log.warning("Scene has outdated content.")

        # Find maya main window
        top_level_widgets = {w.objectName(): w for w in
                             QtWidgets.QApplication.topLevelWidgets()}
        parent = top_level_widgets.get("MayaWindow", None)

        if parent is None:
            log.info("Skipping outdated content pop-up "
                     "because Maya window can't be found.")
        else:

            # Show outdated pop-up
            def _on_show_inventory():
                import avalon.tools.cbsceneinventory as tool
                tool.show(parent=parent)

            dialog = popup.Popup(parent=parent)
            dialog.setWindowTitle("Maya scene has outdated content")
            dialog.setMessage("There are outdated containers in "
                              "your Maya scene.")
            dialog.on_show.connect(_on_show_inventory)
            dialog.show()


def on_task_changed(*args):
    """Wrapped function of app initialize and maya's on task changed"""
    pass