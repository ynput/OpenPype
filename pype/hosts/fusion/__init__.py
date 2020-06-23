import os

from avalon import api as avalon
from pyblish import api as pyblish
from pype import PLUGINS_DIR

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "fusion", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "fusion", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "fusion", "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "fusion", "inventory")


def install():
    print("Registering Fusion plug-ins..")
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
    print("Deregistering Fusion plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    pyblish.deregister_callback("instanceToggled", on_pyblish_instance_toggled)


def on_pyblish_instance_toggled(instance, new_value, old_value):
    """Toggle saver tool passthrough states on instance toggles."""

    from avalon.fusion import comp_lock_and_undo_chunk

    comp = instance.context.data.get("currentComp")
    if not comp:
        return

    savers = [tool for tool in instance if
              getattr(tool, "ID", None) == "Saver"]
    if not savers:
        return

    # Whether instances should be passthrough based on new value
    passthrough = not new_value
    with comp_lock_and_undo_chunk(comp,
                                  undo_queue_name="Change instance "
                                                  "active state"):
        for tool in savers:
            attrs = tool.GetAttrs()
            current = attrs["TOOLB_PassThrough"]
            if current != passthrough:
                tool.SetAttrs({"TOOLB_PassThrough": passthrough})
