import os
import logging

from avalon import api as avalon
from avalon import io
from pyblish import api as pyblish
import openpype.hosts.webpublisher
from openpype.pipeline import LegacyCreator

log = logging.getLogger("openpype.hosts.webpublisher")

HOST_DIR = os.path.dirname(os.path.abspath(
    openpype.hosts.webpublisher.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")


def application_launch():
    pass


def install():
    print("Installing Pype config...")

    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(LegacyCreator, CREATE_PATH)
    log.info(PUBLISH_PATH)

    io.install()
    avalon.on("application.launched", application_launch)


def uninstall():
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(LegacyCreator, CREATE_PATH)


# to have required methods for interface
def ls():
    pass
