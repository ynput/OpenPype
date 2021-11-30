import os
import nuke

import avalon.api
import pyblish.api
import openpype
from . import lib, menu

log = openpype.api.Logger().get_logger(__name__)

AVALON_CONFIG = os.getenv("AVALON_CONFIG", "pype")
HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.nuke.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


# registering pyblish gui regarding settings in presets
if os.getenv("PYBLISH_GUI", None):
    pyblish.api.register_gui(os.getenv("PYBLISH_GUI", None))


def reload_config():
    """Attempt to reload pipeline at run-time.

    CAUTION: This is primarily for development and debugging purposes.

    """

    import importlib

    for module in (
        "{}.api".format(AVALON_CONFIG),
        "{}.hosts.nuke.api.actions".format(AVALON_CONFIG),
        "{}.hosts.nuke.api.menu".format(AVALON_CONFIG),
        "{}.hosts.nuke.api.plugin".format(AVALON_CONFIG),
        "{}.hosts.nuke.api.lib".format(AVALON_CONFIG),
    ):
        log.info("Reloading module: {}...".format(module))

        module = importlib.import_module(module)

        try:
            importlib.reload(module)
        except AttributeError as e:
            from importlib import reload
            log.warning("Cannot reload module: {}".format(e))
            reload(module)


def install():
    ''' Installing all requarements for Nuke host
    '''

    log.info("Registering Nuke plug-ins..")
    pyblish.api.register_plugin_path(PUBLISH_PATH)
    avalon.api.register_plugin_path(avalon.api.Loader, LOAD_PATH)
    avalon.api.register_plugin_path(avalon.api.Creator, CREATE_PATH)
    avalon.api.register_plugin_path(avalon.api.InventoryAction, INVENTORY_PATH)

    # Register Avalon event for workfiles loading.
    avalon.api.on("workio.open_file", lib.check_inventory_versions)

    pyblish.api.register_callback(
        "instanceToggled", on_pyblish_instance_toggled)
    workfile_settings = lib.WorkfileSettings()
    # Disable all families except for the ones we explicitly want to see
    family_states = [
        "write",
        "review",
        "nukenodes",
        "model",
        "gizmo"
    ]

    avalon.api.data["familiesStateDefault"] = False
    avalon.api.data["familiesStateToggled"] = family_states

    # Set context settings.
    nuke.addOnCreate(workfile_settings.set_context_settings, nodeClass="Root")
    nuke.addOnCreate(workfile_settings.set_favorites, nodeClass="Root")
    nuke.addOnCreate(lib.process_workfile_builder, nodeClass="Root")
    nuke.addOnCreate(lib.launch_workfiles_app, nodeClass="Root")
    menu.install()


def uninstall():
    '''Uninstalling host's integration
    '''
    log.info("Deregistering Nuke plug-ins..")
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    avalon.api.deregister_plugin_path(avalon.api.Loader, LOAD_PATH)
    avalon.api.deregister_plugin_path(avalon.api.Creator, CREATE_PATH)

    pyblish.api.deregister_callback(
        "instanceToggled", on_pyblish_instance_toggled)

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
