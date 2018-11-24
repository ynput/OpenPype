import os
import sys
from avalon import api as avalon
from pyblish import api as pyblish
from pype.api import Logger
# import logging
import nuke

# removing logger handler created in avalon_core
loggers = [handler
           for handler in Logger.logging.root.handlers[:]]

if len(loggers) > 2:
    Logger.logging.root.removeHandler(loggers[0])


log = Logger.getLogger(__name__, "nuke")

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

    def emit(self, record):
        # Formated message:
        msg = self.format(record)

        # if record.levelname.lower() is "warning":
        #     nuke.warning(msg)

        elif record.levelname.lower() in ["critical", "fatal", "error"]:
            nuke.message(record.message)

        # elif record.levelname.lower() is "info":
        #     log.info(msg)
        #
        # elif record.levelname.lower() is "debug":
        #     log.debug(msg)

        # else:
        #     sys.stdout.write(msg)


nuke_handler = NukeHandler()
log.addHandler(nuke_handler)
if not self.nLogger:
    self.nLogger = log


def install():

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
