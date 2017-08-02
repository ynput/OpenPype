import os
import site
import uuid

from avalon import maya, io, api as avalon
from pyblish import api as pyblish

from maya import cmds

from . import menu

PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "maya", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "maya", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "maya", "create")


def install():

    # add local pipeline library to the paths
    site.addsitedir(r"P:\pipeline\dev\git\cb")
    site.addsitedir(r"C:\Users\User\Documents\development\cbra")
    site.addsitedir(r"C:\Users\User\Documents\development\pyblish-cb")

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


def on_init():
    avalon.logger.info("Running callback on init..")

    maya.commands.reset_frame_range()
    maya.commands.reset_resolution()


def on_new():
    avalon.logger.info("Running callback on new..")

    # Load dependencies
    cmds.loadPlugin("AbcExport.mll", quiet=True)
    cmds.loadPlugin("AbcImport.mll", quiet=True)

    maya.commands.reset_frame_range()
    maya.commands.reset_resolution()


def on_save(nodes=None):
    """Automatically add IDs to new nodes
    Any transform of a mesh, without an existing ID,
    is given one automatically on file save.
    """

    avalon.logger.info("Running callback on save..")

    defaults = ["initialShadingGroup", "initialParticleSE"]

    # the default items which always want to have an ID
    types = ["mesh", "shadingEngine", "file", "nurbsCurve"]

    # the items which need to pass the id to their parent
    if not nodes:
        nodes = (set(cmds.ls(type=types, long=True)) -
                 set(cmds.ls(long=True, readOnly=True)) -
                 set(cmds.ls(long=True, lockedNodes=True)))

        transforms = set()
        for n in cmds.ls(type=types, long=True):
            # pass id to parent of node if in subtypes
            relatives = cmds.listRelatives(n, parent=True, fullPath=True)
            if not relatives:
                continue

            for r in cmds.listRelatives(n, parent=True, fullPath=True):
                transforms.add(r)

        # merge transforms and nodes in one set to make sure every item
        # is unique
        nodes |= transforms

    # Lead with asset ID from the database
    asset = os.environ["AVALON_ASSET"]
    asset_id = io.find_one({"type": "asset", "name": asset})
    for node in nodes:
        if node in defaults:
            continue
        _set_uuid(str(asset_id["_id"]), node)
