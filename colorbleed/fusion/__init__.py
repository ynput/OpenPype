import os

from avalon import api as avalon
from pyblish import api as pyblish

PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "fusion", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "fusion", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "fusion", "create")


def install():
    print("Registering Fusion plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)


def uninstall():
    print("Deregistering Fusion plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)
