"""
Basic avalon integration
"""
import os

from avalon import api as avalon
from pyblish import api as pyblish
from openpype.api import Logger
import openpype.hosts.fusion

log = Logger().get_logger(__name__)

HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.fusion.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


def install():
    """Install fusion-specific functionality of avalon-core.

    This is where you install menus and register families, data
    and loaders into fusion.

    It is called automatically when installing via `api.install(avalon.fusion)`

    See the Maya equivalent for inspiration on how to implement this.

    """

    log.info("openpype.hosts.fusion installed")

    pyblish.register_host("fusion")
    pyblish.register_plugin_path(PUBLISH_PATH)
    log.info("Registering Fusion plug-ins..")

    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

    pyblish.register_callback("instanceToggled", on_pyblish_instance_toggled)


def uninstall():
    """Uninstall all that was installed

    This is where you undo everything that was done in `install()`.
    That means, removing menus, deregistering families and  data
    and everything. It should be as though `install()` was never run,
    because odds are calling this function means the user is interested
    in re-installing shortly afterwards. If, for example, he has been
    modifying the menu or registered families.

    """
    pyblish.deregister_host("fusion")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    log.info("Deregistering Fusion plug-ins..")

    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.deregister_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

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
