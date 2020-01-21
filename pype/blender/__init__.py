import logging
from pathlib import Path
import os

import bpy

from avalon import api as avalon
from pyblish import api as pyblish

from .plugin import AssetLoader

logger = logging.getLogger("pype.blender")

PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "blender", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "blender", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "blender", "create")


def install():
    """Install Blender configuration for Avalon."""
    pyblish.register_plugin_path(str(PUBLISH_PATH))
    avalon.register_plugin_path(avalon.Loader, str(LOAD_PATH))
    avalon.register_plugin_path(avalon.Creator, str(CREATE_PATH))


def uninstall():
    """Uninstall Blender configuration for Avalon."""
    pyblish.deregister_plugin_path(str(PUBLISH_PATH))
    avalon.deregister_plugin_path(avalon.Loader, str(LOAD_PATH))
    avalon.deregister_plugin_path(avalon.Creator, str(CREATE_PATH))
