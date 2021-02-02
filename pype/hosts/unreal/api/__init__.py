import os
import logging

from avalon import api as avalon
from pyblish import api as pyblish
import pype.hosts.unreal

logger = logging.getLogger("pype.hosts.unreal")

HOST_DIR = os.path.dirname(os.path.abspath(pype.hosts.unreal.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


def install():
    """Install Unreal configuration for Avalon."""
    print("-=" * 40)
    logo = '''.
.
     ____________
   / \\      __   \\
   \\  \\     \\/_\\  \\
    \\  \\     _____/ ______
     \\  \\    \\___// \\     \\
      \\  \\____\\   \\  \\_____\\
       \\/_____/    \\/______/  PYPE Club .
.
'''
    print(logo)
    print("installing Pype for Unreal ...")
    print("-=" * 40)
    logger.info("installing Pype for Unreal")
    pyblish.register_plugin_path(str(PUBLISH_PATH))
    avalon.register_plugin_path(avalon.Loader, str(LOAD_PATH))
    avalon.register_plugin_path(avalon.Creator, str(CREATE_PATH))


def uninstall():
    """Uninstall Unreal configuration for Avalon."""
    pyblish.deregister_plugin_path(str(PUBLISH_PATH))
    avalon.deregister_plugin_path(avalon.Loader, str(LOAD_PATH))
    avalon.deregister_plugin_path(avalon.Creator, str(CREATE_PATH))
