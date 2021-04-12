import os
import sys
import traceback

import bpy

from avalon import api as avalon
from pyblish import api as pyblish

import openpype.hosts.blender

HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.blender.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")

ORIGINAL_EXCEPTHOOK = sys.excepthook


def pype_excepthook_handler(*args):
    traceback.print_exception(*args)


def install():
    """Install Blender configuration for Avalon."""
    sys.excepthook = pype_excepthook_handler
    pyblish.register_plugin_path(str(PUBLISH_PATH))
    avalon.register_plugin_path(avalon.Loader, str(LOAD_PATH))
    avalon.register_plugin_path(avalon.Creator, str(CREATE_PATH))

    avalon.on("new", on_new)
    avalon.on("open", on_open)


def uninstall():
    """Uninstall Blender configuration for Avalon."""
    sys.excepthook = ORIGINAL_EXCEPTHOOK
    pyblish.deregister_plugin_path(str(PUBLISH_PATH))
    avalon.deregister_plugin_path(avalon.Loader, str(LOAD_PATH))
    avalon.deregister_plugin_path(avalon.Creator, str(CREATE_PATH))


def set_start_end_frames():
    from avalon import io

    asset_name = io.Session["AVALON_ASSET"]
    asset_doc = io.find_one({
        "type": "asset",
        "name": asset_name
    })

    # Default frame start/end
    frameStart = 0
    frameEnd = 100

    # Check if frameStart/frameEnd are set
    if asset_doc["data"]["frameStart"]:
        frameStart = asset_doc["data"]["frameStart"]
    if asset_doc["data"]["frameEnd"]:
        frameEnd = asset_doc["data"]["frameEnd"]

    bpy.context.scene.frame_start = frameStart
    bpy.context.scene.frame_end = frameEnd

def on_new(arg1, arg2):
    set_start_end_frames()


def on_open(arg1, arg2):
    set_start_end_frames()
