"""
Basic avalon integration
"""
import os
# import sys
from avalon.tools import workfiles
from avalon import api as avalon
from pyblish import api as pyblish
from pypeapp import Logger

log = Logger().get_logger(__name__, "resolve")

# self = sys.modules[__name__]

AVALON_CONFIG = os.environ["AVALON_CONFIG"]
PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

LOAD_PATH = os.path.join(PLUGINS_DIR, "resolve", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "resolve", "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "resolve", "inventory")

PUBLISH_PATH = os.path.join(
    PLUGINS_DIR, "resolve", "publish"
).replace("\\", "/")

AVALON_CONTAINERS = ":AVALON_CONTAINERS"
# IS_HEADLESS = not hasattr(cmds, "about") or cmds.about(batch=True)


def install():
    """Install resolve-specific functionality of avalon-core.

    This is where you install menus and register families, data
    and loaders into resolve.

    It is called automatically when installing via `api.install(resolve)`.

    See the Maya equivalent for inspiration on how to implement this.

    """

    # Disable all families except for the ones we explicitly want to see
    family_states = [
        "imagesequence",
        "mov"
    ]
    avalon.data["familiesStateDefault"] = False
    avalon.data["familiesStateToggled"] = family_states

    log.info("pype.hosts.resolve installed")

    pyblish.register_host("resolve")
    pyblish.register_plugin_path(PUBLISH_PATH)
    log.info("Registering DaVinci Resovle plug-ins..")

    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)


def uninstall():
    """Uninstall all tha was installed

    This is where you undo everything that was done in `install()`.
    That means, removing menus, deregistering families and  data
    and everything. It should be as though `install()` was never run,
    because odds are calling this function means the user is interested
    in re-installing shortly afterwards. If, for example, he has been
    modifying the menu or registered families.

    """
    pyblish.deregister_host("resolve")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    log.info("Deregistering DaVinci Resovle plug-ins..")

    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.deregister_plugin_path(avalon.InventoryAction, INVENTORY_PATH)


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
    workdir = os.environ["AVALON_WORKDIR"]
    workfiles.show(workdir)


def publish(parent):
    """Shorthand to publish from within host"""
    from avalon.tools import publish
    return publish.show(parent)
