import os
import sys
import traceback

from avalon import api as avalon
from pyblish import api as pyblish

from pype import PLUGINS_DIR

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "blender", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "blender", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "blender", "create")

ORIGINAL_EXCEPTHOOK = sys.excepthook


def pype_excepthook_handler(*args):
    traceback.print_exception(*args)


def install():
    """Install Blender configuration for Avalon."""
    sys.excepthook = pype_excepthook_handler
    pyblish.register_plugin_path(str(PUBLISH_PATH))
    avalon.register_plugin_path(avalon.Loader, str(LOAD_PATH))
    avalon.register_plugin_path(avalon.Creator, str(CREATE_PATH))


def uninstall():
    """Uninstall Blender configuration for Avalon."""
    sys.excepthook = ORIGINAL_EXCEPTHOOK
    pyblish.deregister_plugin_path(str(PUBLISH_PATH))
    avalon.deregister_plugin_path(avalon.Loader, str(LOAD_PATH))
    avalon.deregister_plugin_path(avalon.Creator, str(CREATE_PATH))
