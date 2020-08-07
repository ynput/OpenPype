import os
import sys
import logging

import nuke

from avalon import api as avalon
from avalon.tools import workfiles
from pyblish import api as pyblish
from pype.hosts.nuke import menu
from pype.api import Logger
from pype import PLUGINS_DIR
from . import lib


self = sys.modules[__name__]
self.workfiles_launched = False
log = Logger().get_logger(__name__, "nuke")

AVALON_CONFIG = os.getenv("AVALON_CONFIG", "pype")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "nuke", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "nuke", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "nuke", "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "nuke", "inventory")


# registering pyblish gui regarding settings in presets
if os.getenv("PYBLISH_GUI", None):
    pyblish.register_gui(os.getenv("PYBLISH_GUI", None))


def reload_config():
    """Attempt to reload pipeline at run-time.

    CAUTION: This is primarily for development and debugging purposes.

    """

    import importlib

    for module in (
        "{}.api".format(AVALON_CONFIG),
        "{}.hosts.nuke.actions".format(AVALON_CONFIG),
        "{}.hosts.nuke.presets".format(AVALON_CONFIG),
        "{}.hosts.nuke.menu".format(AVALON_CONFIG),
        "{}.hosts.nuke.plugin".format(AVALON_CONFIG),
        "{}.hosts.nuke.lib".format(AVALON_CONFIG),
    ):
        log.info("Reloading module: {}...".format(module))

        module = importlib.import_module(module)

        try:
            importlib.reload(module)
        except AttributeError as e:
            log.warning("Cannot reload module: {}".format(e))
            reload(module)


def install():
    ''' Installing all requarements for Nuke host
    '''

    log.info("Registering Nuke plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

    # Register Avalon event for workfiles loading.
    avalon.on("workio.open_file", lib.check_inventory_versions)

    pyblish.register_callback("instanceToggled", on_pyblish_instance_toggled)
    workfile_settings = lib.WorkfileSettings()
    # Disable all families except for the ones we explicitly want to see
    family_states = [
        "write",
        "review",
        "nukenodes"
        "gizmo"
    ]

    avalon.data["familiesStateDefault"] = False
    avalon.data["familiesStateToggled"] = family_states

    # Workfiles.
    launch_workfiles = os.environ.get("WORKFILES_STARTUP")

    if launch_workfiles:
        nuke.addOnCreate(launch_workfiles_app, nodeClass="Root")

    # Set context settings.
    nuke.addOnCreate(workfile_settings.set_context_settings, nodeClass="Root")
    nuke.addOnCreate(workfile_settings.set_favorites, nodeClass="Root")

    menu.install()


def launch_workfiles_app():
    '''Function letting start workfiles after start of host
    '''
    if not self.workfiles_launched:
        self.workfiles_launched = True
        workfiles.show(os.environ["AVALON_WORKDIR"])


def uninstall():
    '''Uninstalling host's integration
    '''
    log.info("Deregistering Nuke plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    pyblish.deregister_callback("instanceToggled", on_pyblish_instance_toggled)


    reload_config()
    menu.uninstall()


def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle node passthrough states on instance toggles."""

    log.info("instance toggle: {}, old_value: {}, new_value:{} ".format(
        instance, old_value, new_value))

    from avalon.nuke import (
        viewer_update_and_undo_stop,
        add_publish_knob
    )

    # Whether instances should be passthrough based on new value

    with viewer_update_and_undo_stop():
        n = instance[0]
        try:
            n["publish"].value()
        except ValueError:
            n = add_publish_knob(n)
            log.info(" `Publish` knob was added to write node..")

        n["publish"].setValue(new_value)
