import os
import importlib

from pyblish import api as pyblish
from avalon import api as avalon

from .launcher_actions import register_launcher_actions

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


def _get_host_name():

    _host = avalon.registered_host()
    # This covers nested module name like avalon.maya
    return _host.__name__.rsplit(".", 1)[-1]


def collect_container_metadata(container):
    """Add additional data based on the current host

    If the host application's lib module does not have a function to inject
    additional data it will return the input container

    Args:
        container (dict): collection if representation data in host

    Returns:
        generator
    """

    host_name = _get_host_name()

    # This will cover nested module names like avalon.maya
    package_name = "{}.{}.lib".format(__name__, host_name)
    hostlib = importlib.import_module(package_name)

    if not hasattr(hostlib, "get_additional_data"):
        print("{} has no function called "
              "get_additional_data".format(package_name))
        return container

    return hostlib.get_additional_data(container)
