import os

from pyblish import api as pyblish
from avalon import api as avalon
from .lib import filter_pyblish_plugins

import logging
log = logging.getLogger(__name__)

PACKAGE_DIR = os.path.dirname(__file__)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

# Global plugin paths
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "global", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "global", "load")


def install():
    log.info("Registering global plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    pyblish.register_discovery_filter(filter_pyblish_plugins)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)


def uninstall():
    log.info("Deregistering global plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    pyblish.deregister_discovery_filter(filter_pyblish_plugins)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    log.info("Global plug-ins unregistred")
