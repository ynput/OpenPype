import os
import site
import uuid

from avalon import maya, io, api as avalon
from pyblish import api as pyblish

from maya import cmds

from . import menu
from . import lib

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

    print("Installing callbacks ... ")
    avalon.on("init", on_init)
    avalon.on("new", on_new)
    avalon.on("save", on_save)


def uninstall():
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    menu.uninstall()


def _set_uuid(asset_id, node):
    """Add cbId to `node`
    Unless one already exists.
    """

    attr = "{0}.cbId".format(node)
    if not cmds.attributeQuery("cbId", node=node, exists=True):
        cmds.addAttr(node, longName="cbId", dataType="string")
        _, uid = str(uuid.uuid4()).rsplit("-", 1)
        cb_uid = "{}:{}".format(asset_id, uid)

        cmds.setAttr(attr, cb_uid, type="string")


def _copy_uuid(source, target):

    source_attr = "{0}.cbId".format(source)
    target_attr = "{0}.cbId".format(target)
    if not cmds.attributeQuery("cbId", node=target, exists=True):
        cmds.addAttr(target, longName="cbId", dataType="string")

    attribute_value = cmds.getAttr(source_attr)
    cmds.setAttr(target_attr, attribute_value, type="string")


def on_init(_):
    avalon.logger.info("Running callback on init..")

    maya.commands.reset_frame_range()
    maya.commands.reset_resolution()


def on_new(_):
    avalon.logger.info("Running callback on new..")

    # Load dependencies
    cmds.loadPlugin("AbcExport.mll", quiet=True)
    cmds.loadPlugin("AbcImport.mll", quiet=True)

    maya.commands.reset_frame_range()
    maya.commands.reset_resolution()


def on_save(_):
    """Automatically add IDs to new nodes
    Any transform of a mesh, without an existing ID,
    is given one automatically on file save.
    """

    avalon.logger.info("Running callback on save..")

    nodes = lib.get_id_required_nodes(referenced_nodes=False)

    # Lead with asset ID from the database
    asset = os.environ["AVALON_ASSET"]
    asset_id = io.find_one({"type": "asset", "name": asset},
                           projection={"_id": True})

    # generate the ids

    for node in nodes:
        _set_uuid(str(asset_id["_id"]), node)
