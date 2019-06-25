import os

from pyblish import api as pyblish
from avalon import api as avalon
from Qt import QtWidgets
from .lib import filter_pyblish_plugins

import logging
log = logging.getLogger(__name__)

# # do not delete these are mandatory
Anatomy = None
Dataflow = None
Colorspace = None

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

    # pyblish-qml settings.
    try:
        __import__("pyblish_qml")
    except ImportError as e:
        log.error("Could not load pyblish-qml: %s " % e)
    else:
        from pyblish_qml import settings
        app = QtWidgets.QApplication.instance()
        screen_resolution = app.desktop().screenGeometry()
        width, height = screen_resolution.width(), screen_resolution.height()
        settings.WindowSize = (width / 3, height * 0.75)
        settings.WindowPosition = (0, 0)


def uninstall():
    log.info("Deregistering global plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    pyblish.deregister_discovery_filter(filter_pyblish_plugins)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    log.info("Global plug-ins unregistred")
