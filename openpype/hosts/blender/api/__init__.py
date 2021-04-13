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

    scene = bpy.context.scene

    # Default scene settings
    frameStart = scene.frame_start
    frameEnd = scene.frame_end
    fps = scene.render.fps
    resolution_x = scene.render.resolution_x
    resolution_y = scene.render.resolution_y

    # Check if settings are set
    data = asset_doc.get("data")

    if not data:
        return

    if data.get("frameStart"):
        frameStart = data.get("frameStart")
    if data.get("frameEnd"):
        frameEnd = data.get("frameEnd")
    if data.get("fps"):
        fps = data.get("fps")
    if data.get("resolutionWidth"):
        resolution_x = data.get("resolutionWidth")
    if data.get("resolutionHeight"):
        resolution_y = data.get("resolutionHeight")

    scene.frame_start = frameStart
    scene.frame_end = frameEnd
    scene.render.fps = fps
    scene.render.resolution_x = resolution_x
    scene.render.resolution_y = resolution_y


def on_new(arg1, arg2):
    set_start_end_frames()


def on_open(arg1, arg2):
    set_start_end_frames()
