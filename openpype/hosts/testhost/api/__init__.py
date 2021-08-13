import os
import logging
import pyblish.api
import avalon.api
from openpype.pipeline import BaseCreator

from .pipeline import (
    ls,
    list_instances,
    update_instances,
    remove_instances
)


HOST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")

log = logging.getLogger(__name__)


def install():
    log.info("OpenPype - Installing TestHost integration")
    pyblish.api.register_host("testhost")
    pyblish.api.register_plugin_path(PUBLISH_PATH)
    avalon.api.register_plugin_path(BaseCreator, CREATE_PATH)
