import os
import sys
import logging
import contextlib

import hou

from pyblish import api as pyblish
from avalon import api as avalon

import openpype.hosts.houdini
from openpype.hosts.houdini.api import lib

from openpype.lib import (
    any_outdated
)

from .lib import get_asset_fps

log = logging.getLogger("openpype.hosts.houdini")

HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.houdini.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


def install():

    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)

    log.info("Installing callbacks ... ")
    # avalon.on("init", on_init)
    avalon.before("save", before_save)
    avalon.on("save", on_save)
    avalon.on("open", on_open)
    avalon.on("new", on_new)

    pyblish.register_callback("instanceToggled", on_pyblish_instance_toggled)

    log.info("Setting default family states for loader..")
    avalon.data["familiesStateToggled"] = [
        "imagesequence",
        "review"
    ]

    # add houdini vendor packages
    hou_pythonpath = os.path.join(os.path.dirname(HOST_DIR), "vendor")

    sys.path.append(hou_pythonpath)

    # Set asset FPS for the empty scene directly after launch of Houdini
    # so it initializes into the correct scene FPS
    _set_asset_fps()


def before_save(*args):
    return lib.validate_fps()


def on_save(*args):

    avalon.logger.info("Running callback on save..")

    nodes = lib.get_id_required_nodes()
    for node, new_id in lib.generate_ids(nodes):
        lib.set_id(node, new_id, overwrite=False)


def on_open(*args):

    if not hou.isUIAvailable():
        log.debug("Batch mode detected, ignoring `on_open` callbacks..")
        return

    avalon.logger.info("Running callback on open..")

    # Validate FPS after update_task_from_path to
    # ensure it is using correct FPS for the asset
    lib.validate_fps()

    if any_outdated():
        from openpype.widgets import popup

        log.warning("Scene has outdated content.")

        # Get main window
        parent = hou.ui.mainQtWindow()
        if parent is None:
            log.info("Skipping outdated content pop-up "
                     "because Houdini window can't be found.")
        else:

            # Show outdated pop-up
            def _on_show_inventory():
                import avalon.tools.sceneinventory as tool
                tool.show(parent=parent)

            dialog = popup.Popup(parent=parent)
            dialog.setWindowTitle("Houdini scene has outdated content")
            dialog.setMessage("There are outdated containers in "
                              "your Houdini scene.")
            dialog.on_clicked.connect(_on_show_inventory)
            dialog.show()


def on_new(_):
    """Set project resolution and fps when create a new file"""
    avalon.logger.info("Running callback on new..")
    _set_asset_fps()


def _set_asset_fps():
    """Set Houdini scene FPS to the default required for current asset"""

    # Set new scene fps
    fps = get_asset_fps()
    print("Setting scene FPS to %i" % fps)
    lib.set_scene_fps(fps)


def on_pyblish_instance_toggled(instance, new_value, old_value):
    """Toggle saver tool passthrough states on instance toggles."""
    @contextlib.contextmanager
    def main_take(no_update=True):
        """Enter root take during context"""
        original_take = hou.takes.currentTake()
        original_update_mode = hou.updateModeSetting()
        root = hou.takes.rootTake()
        has_changed = False
        try:
            if original_take != root:
                has_changed = True
                if no_update:
                    hou.setUpdateMode(hou.updateMode.Manual)
                hou.takes.setCurrentTake(root)
                yield
        finally:
            if has_changed:
                if no_update:
                    hou.setUpdateMode(original_update_mode)
                hou.takes.setCurrentTake(original_take)

    if not instance.data.get("_allowToggleBypass", True):
        return

    nodes = instance[:]
    if not nodes:
        return

    # Assume instance node is first node
    instance_node = nodes[0]

    if not hasattr(instance_node, "isBypassed"):
        # Likely not a node that can actually be bypassed
        log.debug("Can't bypass node: %s", instance_node.path())
        return

    if instance_node.isBypassed() != (not old_value):
        print("%s old bypass state didn't match old instance state, "
              "updating anyway.." % instance_node.path())

    try:
        # Go into the main take, because when in another take changing
        # the bypass state of a note cannot be done due to it being locked
        # by default.
        with main_take(no_update=True):
            instance_node.bypass(not new_value)
    except hou.PermissionError as exc:
        log.warning("%s - %s", instance_node.path(), exc)
