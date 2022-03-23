"""
Basic avalon integration
"""
import os
import sys
import logging
import contextlib

import pyblish.api
import avalon.api

from openpype.api import Logger
from openpype.pipeline import (
    LegacyCreator,
    register_loader_plugin_path,
    deregister_loader_plugin_path,
    register_inventory_action_path,
    deregister_inventory_action_path,
    AVALON_CONTAINER_ID,
)
import openpype.hosts.fusion

log = Logger().get_logger(__name__)

HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.fusion.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")

PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


class CompLogHandler(logging.Handler):
    def emit(self, record):
        entry = self.format(record)
        comp = get_current_comp()
        if comp:
            comp.Print(entry)


def install():
    """Install fusion-specific functionality of avalon-core.

    This is where you install menus and register families, data
    and loaders into fusion.

    It is called automatically when installing via `api.install(avalon.fusion)`

    See the Maya equivalent for inspiration on how to implement this.

    """
    # Remove all handlers associated with the root logger object, because
    # that one sometimes logs as "warnings" incorrectly.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Attach default logging handler that prints to active comp
    logger = logging.getLogger()
    formatter = logging.Formatter(fmt="%(message)s\n")
    handler = CompLogHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    log.info("openpype.hosts.fusion installed")

    pyblish.api.register_host("fusion")
    pyblish.api.register_plugin_path(PUBLISH_PATH)
    log.info("Registering Fusion plug-ins..")

    register_loader_plugin_path(LOAD_PATH)
    avalon.api.register_plugin_path(LegacyCreator, CREATE_PATH)
    register_inventory_action_path(INVENTORY_PATH)

    pyblish.api.register_callback(
        "instanceToggled", on_pyblish_instance_toggled
    )


def uninstall():
    """Uninstall all that was installed

    This is where you undo everything that was done in `install()`.
    That means, removing menus, deregistering families and  data
    and everything. It should be as though `install()` was never run,
    because odds are calling this function means the user is interested
    in re-installing shortly afterwards. If, for example, he has been
    modifying the menu or registered families.

    """
    pyblish.api.deregister_host("fusion")
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    log.info("Deregistering Fusion plug-ins..")

    deregister_loader_plugin_path(LOAD_PATH)
    avalon.api.deregister_plugin_path(LegacyCreator, CREATE_PATH)
    deregister_inventory_action_path(INVENTORY_PATH)

    pyblish.api.deregister_callback(
        "instanceToggled", on_pyblish_instance_toggled
    )


def on_pyblish_instance_toggled(instance, new_value, old_value):
    """Toggle saver tool passthrough states on instance toggles."""
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


def ls():
    """List containers from active Fusion scene

    This is the host-equivalent of api.ls(), but instead of listing
    assets on disk, it lists assets already loaded in Fusion; once loaded
    they are called 'containers'

    Yields:
        dict: container

    """

    comp = get_current_comp()
    tools = comp.GetToolList(False, "Loader").values()

    for tool in tools:
        container = parse_container(tool)
        if container:
            yield container


def imprint_container(tool,
                      name,
                      namespace,
                      context,
                      loader=None):
    """Imprint a Loader with metadata

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        tool (object): The node in Fusion to imprint as container, usually a
            Loader.
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        context (dict): Asset information
        loader (str, optional): Name of loader used to produce this container.

    Returns:
        None

    """

    data = [
        ("schema", "openpype:container-2.0"),
        ("id", AVALON_CONTAINER_ID),
        ("name", str(name)),
        ("namespace", str(namespace)),
        ("loader", str(loader)),
        ("representation", str(context["representation"]["_id"])),
    ]

    for key, value in data:
        tool.SetData("avalon.{}".format(key), value)


def parse_container(tool):
    """Returns imprinted container data of a tool

    This reads the imprinted data from `imprint_container`.

    """

    data = tool.GetData('avalon')
    if not isinstance(data, dict):
        return

    # If not all required data return the empty container
    required = ['schema', 'id', 'name',
                'namespace', 'loader', 'representation']
    if not all(key in data for key in required):
        return

    container = {key: data[key] for key in required}

    # Store the tool's name
    container["objectName"] = tool.Name

    # Store reference to the tool object
    container["_tool"] = tool

    return container


def get_current_comp():
    """Hack to get current comp in this session"""
    fusion = getattr(sys.modules["__main__"], "fusion", None)
    return fusion.CurrentComp if fusion else None


@contextlib.contextmanager
def comp_lock_and_undo_chunk(comp, undo_queue_name="Script CMD"):
    """Lock comp and open an undo chunk during the context"""
    try:
        comp.Lock()
        comp.StartUndo(undo_queue_name)
        yield
    finally:
        comp.Unlock()
        comp.EndUndo()
