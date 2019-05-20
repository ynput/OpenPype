import os

from pysync import walktree

from avalon import api as avalon
from pyblish import api as pyblish
from pypeapp import Logger
from .. import api

from ..widgets.message_window import message

import requests

log = Logger().get_logger(__name__, "premiere")

AVALON_CONFIG = os.getenv("AVALON_CONFIG", "pype")
EXTENSIONS_PATH_LOCAL = os.getenv("EXTENSIONS_PATH", None)
EXTENSIONS_PATH_REMOTE = os.path.join(os.path.dirname(__file__), "extensions")
PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

PUBLISH_PATH = os.path.join(
    PLUGINS_DIR, "premiere", "publish"
).replace("\\", "/")

LOAD_PATH = os.path.join(PLUGINS_DIR, "premiere", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "premiere", "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "premiere", "inventory")


def request_aport(url_path, data={}):
    try:
        api.add_tool_to_environment(["aport"])

        ip = os.getenv("PICO_IP", None)
        if ip and ip.startswith('http'):
            ip = ip.replace("http://", "")

        port = int(os.getenv("PICO_PORT", None))

        url = "http://{0}:{1}{2}".format(ip, port, url_path)
        req = requests.post(url, data=data).text
        return req

    except Exception as e:
        message(title="Premiere Aport Server",
                    message="Before you can run Premiere, start Aport Server. \n Error: {}".format(
                        e),
                    level="critical")


def extensions_sync():
    import time
    process_pairs = list()
    # get extensions dir in pype.premiere.extensions
    # build dir path to premiere cep extensions
    for name in os.listdir(EXTENSIONS_PATH_REMOTE):
        print(name)
        src = os.path.join(EXTENSIONS_PATH_REMOTE, name)
        dst = os.path.join(EXTENSIONS_PATH_LOCAL, name)
        process_pairs.append((name, src, dst))

    # synchronize all extensions
    for name, src, dst in process_pairs:
        if not os.path.exists(dst):
            os.makedirs(dst, mode=0o777)
        walktree(source=src, target=dst, options_input=["y", ">"])
        log.info("Extension {0} from `{1}` coppied to `{2}`".format(
            name, src, dst
        ))
    time.sleep(10)
    return


def install():

    api.set_avalon_workdir()
    log.info("Registering Premiera plug-ins..")

    reg_paths = request_aport("/api/register_plugin_path",
                              {"publish_path": PUBLISH_PATH})

    log.info(str(reg_paths))

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

    # synchronize extensions
    extensions_sync()
    message(title="pyblish_paths", message=str(reg_paths), level="info")


def uninstall():
    log.info("Deregistering Premiera plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    # reset data from templates
    api.reset_data_from_templates()
