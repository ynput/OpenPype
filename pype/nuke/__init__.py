import os

from avalon import api as avalon
from pyblish import api as pyblish

PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "nuke", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "nuke", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "nuke", "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "nuke", "inventory")


def install():
    print("Registering Nuke plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

    pyblish.register_callback("instanceToggled", on_pyblish_instance_toggled)

    # Disable all families except for the ones we explicitly want to see
    family_states = ["imagesequence",
                     "camera",
                     "pointcache"]

    avalon.data["familiesStateDefault"] = False
    avalon.data["familiesStateToggled"] = family_states


def uninstall():
    print("Deregistering Nuke plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    pyblish.deregister_callback("instanceToggled", on_pyblish_instance_toggled)


def on_pyblish_instance_toggled(instance, new_value, old_value):
    """Toggle saver tool passthrough states on instance toggles."""

    from avalon.nuke import viewer_update_and_undo_stop, add_publish_knob, log

    writes = [n for n in instance if
              n.Class() == "Write"]
    if not writes:
        return

    # Whether instances should be passthrough based on new value
    passthrough = not new_value
    with viewer_update_and_undo_stop():
        for n in writes:
            try:
                n["publish"].value()
            except ValueError:
                n = add_publish_knob(n)
                log.info(" `Publish` knob was added to write node..")

            current = n["publish"].value()
            if current != passthrough:
                n["publish"].setValue(passthrough)
