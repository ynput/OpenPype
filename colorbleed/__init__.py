import os
from pyblish import api as pyblish
from avalon import api as avalon

from .launcher_actions import register_launcher_actions
from .manager_actions import register_manager_actions

PACKAGE_DIR = os.path.dirname(__file__)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

# Global plugin paths
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "global", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "global", "load")


def install():
    print("Registering global plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)


def uninstall():
    print("Deregistering global plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)

