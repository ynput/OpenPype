import os
import sys
from avalon import api as avalon
from pyblish import api as pyblish

from .. import api

from pype.nukestudio import menu

from .lib import (
    show,
    setup,
    register_plugins,
    add_to_filemenu
)

import nuke

from pypeapp import Logger


log = Logger().get_logger(__name__, "nuke")

AVALON_CONFIG = os.getenv("AVALON_CONFIG", "pype")

PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "nukestudio", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "nukestudio", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "nukestudio", "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "nukestudio", "inventory")


if os.getenv("PYBLISH_GUI", None):
    pyblish.register_gui(os.getenv("PYBLISH_GUI", None))


def reload_config():
    """Attempt to reload pipeline at run-time.

    CAUTION: This is primarily for development and debugging purposes.

    """

    import importlib

    for module in (
        "pypeapp",
        "{}.api".format(AVALON_CONFIG),
        "{}.templates".format(AVALON_CONFIG),
        "{}.nukestudio.inventory".format(AVALON_CONFIG),
        "{}.nukestudio.lib".format(AVALON_CONFIG),
        "{}.nukestudio.menu".format(AVALON_CONFIG),
    ):
        log.info("Reloading module: {}...".format(module))
        try:
            module = importlib.import_module(module)
            reload(module)
        except Exception as e:
            log.warning("Cannot reload module: {}".format(e))
            importlib.reload(module)


def install():

    # api.set_avalon_workdir()
    # reload_config()

    import sys

    # for path in sys.path:
    #     if path.startswith("C:\\Users\\Public"):
    #         sys.path.remove(path)

    log.info("Registering Nuke plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

    # Disable all families except for the ones we explicitly want to see
    family_states = [
        "write",
        "review"
    ]

    avalon.data["familiesStateDefault"] = False
    avalon.data["familiesStateToggled"] = family_states

    menu.install()

    # load data from templates
    api.load_data_from_templates()


def uninstall():
    log.info("Deregistering Nuke plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    # reset data from templates
    api.reset_data_from_templates()
