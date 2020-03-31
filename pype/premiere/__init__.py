import os
import sys
import shutil

from pysync import walktree

from avalon import api as avalon
from pyblish import api as pyblish
from app import api as app
from .. import api
import requests

from .pipeline import (
    install,
    uninstall,
    reload_pipeline,
    ls
)

__all__ = [
    "install",
    "uninstall",
    "reload_pipeline",
    "ls"
]

log = api.Logger.getLogger(__name__, "premiere")

AVALON_CONFIG = os.getenv("AVALON_CONFIG", "pype")
EXTENSIONS_PATH_LOCAL = os.getenv("EXTENSIONS_PATH", None)
EXTENSIONS_CACHE_PATH = os.getenv("EXTENSIONS_CACHE_PATH", None)
EXTENSIONS_PATH_REMOTE = os.path.join(os.path.dirname(__file__), "extensions")
PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

_clearing_cache = ["com.pype.rename", "com.pype.avalon"]

PUBLISH_PATH = os.path.join(
    PLUGINS_DIR, "premiere", "publish"
).replace("\\", "/")

if os.getenv("PUBLISH_PATH", None):
    os.environ["PUBLISH_PATH"] = os.pathsep.join(
        os.environ["PUBLISH_PATH"].split(os.pathsep) +
        [PUBLISH_PATH]
    )
else:
    os.environ["PUBLISH_PATH"] = PUBLISH_PATH

LOAD_PATH = os.path.join(PLUGINS_DIR, "premiere", "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "premiere", "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "premiere", "inventory")

log.debug("_clearing_cache: {}".format(_clearing_cache))

def clearing_caches_ui():
    '''Before every start of premiere it will make sure there is not
    outdated stuff in cep_cache dir'''

    for d in os.listdir(EXTENSIONS_CACHE_PATH):
        match = [p for p in _clearing_cache
                if str(p) in d]

        if match:
            try:
                path = os.path.normpath(os.path.join(EXTENSIONS_CACHE_PATH, d))
                log.info("Removing dir: {}".format(path))
                shutil.rmtree(path, ignore_errors=True)
            except Exception as e:
                log.debug("problem: {}".format(e))

def request_aport(url_path, data={}):
    try:
        api.add_tool_to_environment(["aport_0.1"])

        ip = os.getenv("PICO_IP", None)
        if ip and ip.startswith('http'):
            ip = ip.replace("http://", "")

        port = int(os.getenv("PICO_PORT", None))

        url = "http://{0}:{1}{2}".format(ip, port, url_path)
        req = requests.post(url, data=data).text
        return req

    except Exception as e:
        api.message(title="Premiere Aport Server",
                    message="Before you can run Premiere, start Aport Server. \n Error: {}".format(
                        e),
                    level="critical")


def extensions_sync():
    # import time
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
    # time.sleep(10)
    return


def install():

    log.info("Registering Premiera plug-ins..")
    reg_paths = request_aport("/api/register_plugin_path",
                              {"publish_path": PUBLISH_PATH})

    # Disable all families except for the ones we explicitly want to see
    family_states = [
        "imagesequence",
        "mov"

    ]
    avalon.data["familiesStateDefault"] = False
    avalon.data["familiesStateToggled"] = family_states

    # load data from templates
    api.load_data_from_templates()

    # remove cep_cache from user temp dir
    clearing_caches_ui()

    # synchronize extensions
    extensions_sync()
    message = "The Pype extension has been installed. " \
        "\nThe following publishing paths has been registered: " \
        "\n\n{}".format(
            reg_paths)

    api.message(title="pyblish_paths", message=message, level="info")

    # launching premiere
    exe = r"C:\Program Files\Adobe\Adobe Premiere Pro CC 2019\Adobe Premiere Pro.exe".replace(
        "\\", "/")

    log.info("____path exists: {}".format(os.path.exists(exe)))

    app.forward(args=[exe],
                silent=False,
                cwd=os.getcwd(),
                env=dict(os.environ),
                shell=None)


def uninstall():
    log.info("Deregistering Premiera plug-ins..")
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)

    # reset data from templates
    api.reset_data_from_templates()
