"""
Basic avalon integration
"""
import os
import contextlib
from avalon.tools import (
    workfiles,
    publish as _publish
)
from avalon import api as avalon
from pyblish import api as pyblish
import pype
from pype.api import Logger

from .events import register_hiero_events, register_events
from .menu import menu_install

log = Logger().get_logger(__name__, "hiero")

AVALON_CONFIG = os.getenv("AVALON_CONFIG", "pype")

# plugin paths
LOAD_PATH = os.path.join(pype.PLUGINS_DIR, "hiero", "load")
CREATE_PATH = os.path.join(pype.PLUGINS_DIR, "hiero", "create")
INVENTORY_PATH = os.path.join(pype.PLUGINS_DIR, "hiero", "inventory")

PUBLISH_PATH = os.path.join(
    pype.PLUGINS_DIR, "hiero", "publish"
).replace("\\", "/")

AVALON_CONTAINERS = ":AVALON_CONTAINERS"


def install():
    """
    Installing Hiero integration for avalon

    Args:
        config (obj): avalon config module `pype` in our case, it is not
        used but required by avalon.api.install()

    """

    # adding all events
    register_events()

    log.info("Registering Hiero plug-ins..")
    pyblish.register_host("hiero")
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

    # Disable all families except for the ones we explicitly want to see
    family_states = [
        "write",
        "review",
        "plate"
    ]

    avalon.data["familiesStateDefault"] = False
    avalon.data["familiesStateToggled"] = family_states

    # install menu
    menu_install()

    # register hiero events
    register_hiero_events()


def uninstall():
    """
    Uninstalling Hiero integration for avalon

    """
    log.info("Deregistering Hiero plug-ins..")
    pyblish.deregister_host("hiero")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)


def containerise(obj,
                 name,
                 namespace,
                 context,
                 loader=None,
                 data=None):
    """Bundle Resolve's object into an assembly and imprint it with metadata

    Containerisation enables a tracking of version, author and origin
    for loaded assets.

    Arguments:
        obj (obj): Resolve's object to imprint as container
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        context (dict): Asset information
        loader (str, optional): Name of node used to produce this container.

    Returns:
        obj (obj): containerised object

    """
    pass


def ls():
    """List available containers.

    This function is used by the Container Manager in Nuke. You'll
    need to implement a for-loop that then *yields* one Container at
    a time.

    See the `container.json` schema for details on how it should look,
    and the Maya equivalent, which is in `avalon.maya.pipeline`
    """
    pass


def parse_container(container):
    """Return the container node's full container data.

    Args:
        container (str): A container node name.

    Returns:
        dict: The container schema data for this container node.

    """
    pass


def launch_workfiles_app(*args):
    ''' Wrapping function for workfiles launcher '''

    workdir = os.environ["AVALON_WORKDIR"]

    # show workfile gui
    workfiles.show(workdir)


def publish(parent):
    """Shorthand to publish from within host"""
    return _publish.show(parent)


@contextlib.contextmanager
def maintained_selection():
    """Maintain selection during context

    Example:
        >>> with maintained_selection():
        ...     node['selected'].setValue(True)
        >>> print(node['selected'].value())
        False
    """
    try:
        # do the operation
        yield
    finally:
        pass


def reset_selection():
    """Deselect all selected nodes
    """
    pass


def reload_config():
    """Attempt to reload pipeline at run-time.

    CAUTION: This is primarily for development and debugging purposes.

    """
    import importlib

    for module in (
        "avalon",
        "avalon.lib",
        "avalon.pipeline",
        "pyblish",
        "pypeapp",
        "{}.api".format(AVALON_CONFIG),
        "{}.hosts.hiero.lib".format(AVALON_CONFIG),
        "{}.hosts.hiero.menu".format(AVALON_CONFIG),
        "{}.hosts.hiero.tags".format(AVALON_CONFIG)
    ):
        log.info("Reloading module: {}...".format(module))
        try:
            module = importlib.import_module(module)
            import imp
            imp.reload(module)
        except Exception as e:
            log.warning("Cannot reload module: {}".format(e))
            importlib.reload(module)
