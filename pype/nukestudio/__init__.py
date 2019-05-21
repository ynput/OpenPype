import os
import sys
from avalon import api as avalon
from pyblish import api as pyblish

from .. import api

from .menu import install as menu_install

from .lib import (
    show,
    setup,
    add_to_filemenu
)


from pypeapp import Logger


log = Logger().get_logger(__name__, "nukestudio")

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


def install(config):

    # api.set_avalon_workdir()
    # reload_config()

    # import sys
    # for path in sys.path:
    #     if path.startswith("C:\\Users\\Public"):
    #         sys.path.remove(path)

    log.info("Registering NukeStudio plug-ins..")
    pyblish.register_host("nukestudio")
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

    menu_install()

    # load data from templates
    api.load_data_from_templates()



def uninstall():
    log.info("Deregistering NukeStudio plug-ins..")
    pyblish.deregister_host("nukestudio")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    # reset data from templates
    api.reset_data_from_templates()


def ls():
    """List available containers.

    This function is used by the Container Manager in Nuke. You'll
    need to implement a for-loop that then *yields* one Container at
    a time.

    See the `container.json` schema for details on how it should look,
    and the Maya equivalent, which is in `avalon.maya.pipeline`
    """
    return
