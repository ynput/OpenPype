import os
import logging

import hou

from pyblish import api as pyblish

from avalon import api as avalon
from avalon.houdini import pipeline as houdini

from pype.hosts.houdini import lib

from pype.lib import any_outdated
from pype import PLUGINS_DIR

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "houdini", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "houdini", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "houdini", "create")

log = logging.getLogger("pype.hosts.houdini")


def install():

    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)

    log.info("Installing callbacks ... ")
    avalon.on("init", on_init)
    avalon.before("save", before_save)
    avalon.on("save", on_save)
    avalon.on("open", on_open)

    pyblish.register_callback("instanceToggled", on_pyblish_instance_toggled)

    log.info("Setting default family states for loader..")
    avalon.data["familiesStateToggled"] = ["imagesequence"]


def on_init(*args):
    houdini.on_houdini_initialize()


def before_save(*args):
    return lib.validate_fps()


def on_save(*args):

    avalon.logger.info("Running callback on save..")

    nodes = lib.get_id_required_nodes()
    for node, new_id in lib.generate_ids(nodes):
        lib.set_id(node, new_id, overwrite=False)


def on_open(*args):

    avalon.logger.info("Running callback on open..")

    if any_outdated():
        from ..widgets import popup

        log.warning("Scene has outdated content.")

        # Get main window
        parent = hou.ui.mainQtWindow()
        if parent is None:
            log.info("Skipping outdated content pop-up "
                     "because Maya window can't be found.")
        else:

            # Show outdated pop-up
            def _on_show_inventory():
                import avalon.tools.sceneinventory as tool
                tool.show(parent=parent)

            dialog = popup.Popup(parent=parent)
            dialog.setWindowTitle("Maya scene has outdated content")
            dialog.setMessage("There are outdated containers in "
                              "your Maya scene.")
            dialog.on_show.connect(_on_show_inventory)
            dialog.show()


def on_pyblish_instance_toggled(instance, new_value, old_value):
    """Toggle saver tool passthrough states on instance toggles."""

    nodes = instance[:]
    if not nodes:
        return

    # Assume instance node is first node
    instance_node = nodes[0]

    if instance_node.isBypassed() != (not old_value):
        print("%s old bypass state didn't match old instance state, "
              "updating anyway.." % instance_node.path())

    instance_node.bypass(not new_value)
