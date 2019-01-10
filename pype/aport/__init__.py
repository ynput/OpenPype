import os
import sys

from avalon import api as avalon
from pyblish import api as pyblish
from app import api as app

from .. import api

log = api.Logger.getLogger(__name__, "aport")

AVALON_CONFIG = os.getenv("AVALON_CONFIG", "pype")

PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

PUBLISH_PATH = os.path.join(
    PLUGINS_DIR, "aport", "publish"
).replace("\\", "/")

if os.getenv("PUBLISH_PATH", None):
    os.environ["PUBLISH_PATH"] = os.pathsep.join(
        os.environ["PUBLISH_PATH"].split(os.pathsep) +
        [PUBLISH_PATH]
    )
else:
    os.environ["PUBLISH_PATH"] = PUBLISH_PATH

LOAD_PATH = os.path.join(PLUGINS_DIR, "aport", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "aport", "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "aport", "inventory")


def install():
    api.set_avalon_workdir()

    log.info("Registering Aport plug-ins..")
    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    avalon.register_plugin_path(avalon.InventoryAction, INVENTORY_PATH)

    # Disable all families except for the ones we explicitly want to see
    family_states = [
        "imagesequence",
        "mov"

    ]
    avalon.data["familiesStateDefault"] = False
    avalon.data["familiesStateToggled"] = family_states

    # load data from templates
    api.load_data_from_templates()

    # launch pico server
    pico_server_launch()


def uninstall():
    log.info("Deregistering Aport plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    # reset data from templates
    api.reset_data_from_templates()


def pico_server_launch():
    try:
        args = [sys.executable, "-m", "pico.server", "pipeline"]

        app.forward(
            args,
            cwd=os.path.dirname(__file__)
        )
    except Exception as e:
        log.error(e)
        log.error(sys.exc_info())
    # sys.exit(returncode)
