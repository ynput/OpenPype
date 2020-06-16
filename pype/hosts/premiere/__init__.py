from avalon import api as avalon
from pyblish import api as pyblish
from pype.api import Logger


from .lib import (
    setup,
    reload_pipeline,
    ls,
    LOAD_PATH,
    CREATE_PATH,
    PUBLISH_PATH
)

__all__ = [
    "setup",
    "reload_pipeline",
    "ls"
]

log = Logger().get_logger(__name__, "premiere")


def install():
    """Install Premiere-specific functionality of avalon-core.

    This is where you install menus and register families, data
    and loaders into Premiere.

    It is called automatically when installing via `api.install(premiere)`.

    See the Maya equivalent for inspiration on how to implement this.

    """

    # Disable all families except for the ones we explicitly want to see
    family_states = [
        "imagesequence",
        "mov"
    ]
    avalon.data["familiesStateDefault"] = False
    avalon.data["familiesStateToggled"] = family_states

    log.info("pype.hosts.premiere installed")

    pyblish.register_host("premiere")
    pyblish.register_plugin_path(PUBLISH_PATH)
    log.info("Registering Premiera plug-ins..")

    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)


def uninstall():
    """Uninstall all tha was installed

    This is where you undo everything that was done in `install()`.
    That means, removing menus, deregistering families and  data
    and everything. It should be as though `install()` was never run,
    because odds are calling this function means the user is interested
    in re-installing shortly afterwards. If, for example, he has been
    modifying the menu or registered families.

    """
    pyblish.deregister_host("premiere")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    log.info("Deregistering Premiera plug-ins..")

    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)
