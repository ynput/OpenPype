import os
import logging

from pyblish import api as pyblish
import openpype.hosts.webpublisher
from openpype.pipeline import legacy_io

log = logging.getLogger("openpype.hosts.webpublisher")

HOST_DIR = os.path.dirname(os.path.abspath(
    openpype.hosts.webpublisher.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")


def install():
    print("Installing Pype config...")

    pyblish.register_plugin_path(PUBLISH_PATH)
    log.info(PUBLISH_PATH)

    legacy_io.install()


def uninstall():
    pyblish.deregister_plugin_path(PUBLISH_PATH)


# to have required methods for interface
def ls():
    pass
