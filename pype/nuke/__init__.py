import os
import sys
from avalon import api as avalon
from pyblish import api as pyblish
from ..api import Logger
from pype.nuke import menu

import nuke

# removing logger handler created in avalon_core
for name, handler in [(handler.get_name(), handler)
                      for handler in Logger.logging.root.handlers[:]]:
    if "pype" not in str(name).lower():
        Logger.logging.root.removeHandler(handler)


log = Logger.getLogger(__name__, "nuke")

AVALON_CONFIG = os.getenv("AVALON_CONFIG", "pype")

PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "nuke", "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "nuke", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "nuke", "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "nuke", "inventory")

self = sys.modules[__name__]
self.nLogger = None


class NukeHandler(Logger.logging.Handler):
    '''
    Nuke Handler - emits logs into nuke's script editor.
    warning will emit nuke.warning()
    critical and fatal would popup msg dialog to alert of the error.
    '''

    def __init__(self):
        Logger.logging.Handler.__init__(self)
        self.set_name("Pype_Nuke_Handler")

    def emit(self, record):
        # Formated message:
        msg = self.format(record)

        if record.levelname.lower() in [
            "warning",
            "critical",
            "fatal",
            "error"
        ]:
            nuke.message(msg)


'''Adding Nuke Logging Handler'''
nuke_handler = NukeHandler()
if nuke_handler.get_name() \
    not in [handler.get_name()
            for handler in Logger.logging.root.handlers[:]]:
    Logger.logging.getLogger().addHandler(nuke_handler)

if not self.nLogger:
    self.nLogger = Logger


def reload_config():
    """Attempt to reload pipeline at run-time.

    CAUTION: This is primarily for development and debugging purposes.

    """

    import importlib

    for module in (
        "{}".format(AVALON_CONFIG),
        "{}.nuke".format(AVALON_CONFIG),
        "{}.nuke.lib".format(AVALON_CONFIG),
        "{}.nuke.menu".format(AVALON_CONFIG)
    ):
        log.info("Reloading module: {}...".format(module))
        module = importlib.import_module(module)
        try:
            reload(module)
        except Exception:
            importlib.reload(module)


def install():
    reload_config()
    log.info("Registering Nuke plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

    pyblish.register_callback("instanceToggled", on_pyblish_instance_toggled)

    # Disable all families except for the ones we explicitly want to see
    family_states = [
        "imagesequence",
        "mov"
        "camera",
        "pointcache",
    ]

    avalon.data["familiesStateDefault"] = False
    avalon.data["familiesStateToggled"] = family_states

    menu.install()


def uninstall():
    log.info("Deregistering Nuke plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    pyblish.deregister_callback("instanceToggled", on_pyblish_instance_toggled)


def on_pyblish_instance_toggled(instance, new_value, old_value):
    """Toggle saver tool passthrough states on instance toggles."""

    from avalon.nuke import (
        viewer_update_and_undo_stop,
        add_publish_knob
    )

    writes = [n for n in instance if
              n.Class() is "Write"]
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
