import os
import logging

from avalon.tvpaint.communication_server import register_localization_file
import avalon.api
import pyblish.api
from pype import PLUGINS_DIR

log = logging.getLogger("pype.hosts.tvpaint")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "tvpaint", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "tvpaint", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "tvpaint", "create")


def install():
    log.info("Pype - Installing TVPaint integration")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    localization_file = os.path.join(current_dir, "avalon.loc")
    register_localization_file(localization_file)

    pyblish.api.register_plugin_path(PUBLISH_PATH)
    avalon.api.register_plugin_path(avalon.api.Loader, LOAD_PATH)
    avalon.api.register_plugin_path(avalon.api.Creator, CREATE_PATH)


def uninstall():
    log.info("Pype - Uninstalling TVPaint integration")
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    avalon.api.deregister_plugin_path(avalon.api.Loader, LOAD_PATH)
    avalon.api.deregister_plugin_path(avalon.api.Creator, CREATE_PATH)
