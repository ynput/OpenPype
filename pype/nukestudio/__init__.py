import os

from avalon.tools import workfiles
from avalon import api as avalon
from pyblish import api as pyblish

from .. import api
from .menu import (
    install as menu_install,
    _update_menu_task_label
)
from .tags import add_tags_from_presets

from pypeapp import Logger

import hiero

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


def install(config):

    _register_events()

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

    # Workfiles.
    launch_workfiles = os.environ.get("WORKFILES_STARTUP")

    if launch_workfiles:
        hiero.core.events.registerInterest(
            "kAfterNewProjectCreated", launch_workfiles_app
        )

    # Add tags on project load.
    hiero.core.events.registerInterest(
        "kAfterProjectLoad", add_tags
    )


def add_tags(event):
    add_tags_from_presets()


def launch_workfiles_app(event):
    workfiles.show(os.environ["AVALON_WORKDIR"])

    # Closing the new project.
    event.sender.close()

    # Deregister interest as its a one-time launch.
    hiero.core.events.unregisterInterest(
        "kAfterNewProjectCreated", launch_workfiles_app
    )


def uninstall():
    log.info("Deregistering NukeStudio plug-ins..")
    pyblish.deregister_host("nukestudio")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    # reset data from templates
    api.reset_data_from_templates()


def _register_events():
    avalon.on("taskChanged", _update_menu_task_label)
    log.info("Installed event callback for 'taskChanged'..")


def ls():
    """List available containers.

    This function is used by the Container Manager in Nuke. You'll
    need to implement a for-loop that then *yields* one Container at
    a time.

    See the `container.json` schema for details on how it should look,
    and the Maya equivalent, which is in `avalon.maya.pipeline`
    """
    return
