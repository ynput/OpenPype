import os
import sys
import shutil
import json
from pysync import walktree
import requests

from avalon import api
from pype.widgets.message_window import message
from pypeapp import Logger


log = Logger().get_logger(__name__, "resolve")

self = sys.modules[__name__]
self._has_been_setup = False
self._registered_gui = None

AVALON_CONFIG = os.environ["AVALON_CONFIG"]

PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

self.EXTENSIONS_PATH_REMOTE = os.path.join(PARENT_DIR, "extensions")
self.EXTENSIONS_PATH_LOCAL = None
self.EXTENSIONS_CACHE_PATH = None

self.LOAD_PATH = os.path.join(PLUGINS_DIR, "resolve", "load")
self.CREATE_PATH = os.path.join(PLUGINS_DIR, "resolve", "create")
self.INVENTORY_PATH = os.path.join(PLUGINS_DIR, "resolve", "inventory")

self.PUBLISH_PATH = os.path.join(
    PLUGINS_DIR, "resolve", "publish"
).replace("\\", "/")

if os.getenv("PUBLISH_PATH", None):
    if self.PUBLISH_PATH not in os.environ["PUBLISH_PATH"]:
        os.environ["PUBLISH_PATH"] = os.pathsep.join(
            os.environ["PUBLISH_PATH"].split(os.pathsep) +
            [self.PUBLISH_PATH]
        )
else:
    os.environ["PUBLISH_PATH"] = self.PUBLISH_PATH


def ls():
    pass


def reload_pipeline():
    """Attempt to reload pipeline at run-time.

    CAUTION: This is primarily for development and debugging purposes.

    """

    import importlib
    import pype.resolve

    api.uninstall()

    for module in ("avalon.io",
                   "avalon.lib",
                   "avalon.pipeline",
                   "avalon.api",
                   "avalon.tools",

                   "{}".format(AVALON_CONFIG),
                   "{}.resolve".format(AVALON_CONFIG),
                   "{}.resolve.lib".format(AVALON_CONFIG)
                   ):
        log.info("Reloading module: {}...".format(module))
        try:
            module = importlib.import_module(module)
            importlib.reload(module)
        except Exception as e:
            log.warning("Cannot reload module: {}".format(e))

    api.install(pype.resolve)


def setup(env=None):
    """ Running wrapper
    """
    if not env:
        env = os.environ

    log.info("Resolve Pype wrapper has been installed")
