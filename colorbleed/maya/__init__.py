import os
import logging
from functools import partial

from maya import utils
from maya import cmds

from avalon import api as avalon
from pyblish import api as pyblish

from . import menu
from . import lib

log = logging.getLogger("colorbleed.maya")

PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "maya", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "maya", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "maya", "create")


def install():
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)

    menu.install()

    log.info("Installing callbacks ... ")
    avalon.on("init", on_init)
    avalon.on("save", on_save)


def uninstall():
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    menu.uninstall()


def on_init(_):
    avalon.logger.info("Running callback on init..")

    def force_load_deferred(plugin):
        """Load a plug-in deferred so it runs after UI has initialized"""
        try:
            utils.executeDeferred(partial(cmds.loadPlugin,
                                          plugin,
                                          quiet=True))
        except RuntimeError, e:
            log.warning("Can't load plug-in: "
                        "{0} - {1}".format(plugin, e))

    def safe_deferred(fn):
        """Execute deferred the function in a try-except"""

        def _fn():
            """safely call in deferred callback"""
            try:
                fn()
            except Exception as exc:
                print(exc)

        try:
            utils.executeDeferred(_fn)
        except Exception as exc:
            print(exc)


    cmds.loadPlugin("AbcImport", quiet=True)
    cmds.loadPlugin("AbcExport", quiet=True)
    force_load_deferred("mtoa")

    from .customize import override_component_mask_commands
    safe_deferred(override_component_mask_commands)


def on_save(_):
    """Automatically add IDs to new nodes
    Any transform of a mesh, without an existing ID,
    is given one automatically on file save.
    """

    avalon.logger.info("Running callback on save..")

    # Generate ids of the current context on nodes in the scene
    nodes = lib.get_id_required_nodes(referenced_nodes=False)
    for node, new_id in lib.generate_ids(nodes):
        lib.set_id(node, new_id, overwrite=False)
