import os
import sys
import shutil
import json
from pysync import walktree
import requests

from avalon import api
from pype.widgets.message_window import message
from pype import PLUGINS_DIR
from pype.api import Logger

log = Logger().get_logger(__name__, "premiere")

self = sys.modules[__name__]
self._has_been_setup = False
self._registered_gui = None

AVALON_CONFIG = os.environ["AVALON_CONFIG"]

PARENT_DIR = os.path.dirname(__file__)

self.EXTENSIONS_PATH_REMOTE = os.path.join(PARENT_DIR, "extensions")
self.EXTENSIONS_PATH_LOCAL = None
self.EXTENSIONS_CACHE_PATH = None

self.LOAD_PATH = os.path.join(PLUGINS_DIR, "premiere", "load")
self.CREATE_PATH = os.path.join(PLUGINS_DIR, "premiere", "create")
self.INVENTORY_PATH = os.path.join(PLUGINS_DIR, "premiere", "inventory")

self.PUBLISH_PATH = os.path.join(
    PLUGINS_DIR, "premiere", "publish"
).replace("\\", "/")

if os.getenv("PUBLISH_PATH", None):
    if self.PUBLISH_PATH not in os.environ["PUBLISH_PATH"]:
        os.environ["PUBLISH_PATH"] = os.pathsep.join(
            os.environ["PUBLISH_PATH"].split(os.pathsep) +
            [self.PUBLISH_PATH]
        )
else:
    os.environ["PUBLISH_PATH"] = self.PUBLISH_PATH

_clearing_cache = ["com.pype", "com.pype.rename"]


def ls():
    pass


def reload_pipeline():
    """Attempt to reload pipeline at run-time.

    CAUTION: This is primarily for development and debugging purposes.

    """

    import importlib
    import pype.hosts.premiere

    api.uninstall()

    for module in ("avalon.io",
                   "avalon.lib",
                   "avalon.pipeline",
                   "avalon.api",
                   "avalon.tools",

                   "{}".format(AVALON_CONFIG),
                   "{}.premiere".format(AVALON_CONFIG),
                   "{}.premiere.lib".format(AVALON_CONFIG)
                   ):
        log.info("Reloading module: {}...".format(module))
        try:
            module = importlib.import_module(module)
            importlib.reload(module)
        except Exception as e:
            log.warning("Cannot reload module: {}".format(e))

    api.install(pype.hosts.premiere)


def setup(env=None):
    """ Running wrapper
    """
    if not env:
        env = os.environ

    self.EXTENSIONS_PATH_LOCAL = env["EXTENSIONS_PATH"]
    self.EXTENSIONS_CACHE_PATH = env["EXTENSIONS_CACHE_PATH"]

    log.info("Registering Adobe Premiere plug-ins..")
    if not test_rest_api_server(env):
        return

    if not env.get("installed_zxp"):
        # remove cep_cache from user temp dir
        clearing_caches_ui()

        # synchronize extensions
        extensions_sync()
    else:
        log.info("Extensions installed as `.zxp`...")

    log.info("Premiere Pype wrapper has been installed")


def extensions_sync():
    # TODO(antirotor): Bundle extension and install it
    # we need to bundle extension as we are using third party node_modules
    # to ease creation of bundle, lets create build script creating self-signed
    # certificate and bundling extension to zxp format (using ZXPSignCmd from
    # Adobe). If we find zxp in extension directory, we can install it via
    # command line `ExManCmd /install` - using Adobe Extension Manager. If
    # zxp is not found, we use old behaviour and just copy all files. Thus we
    # maintain ability to develop and deploy at the same time.
    #
    # sources:
    # https://helpx.adobe.com/extension-manager/using/command-line.html

    process_pairs = list()
    # get extensions dir in pype.hosts.premiere.extensions
    # build dir path to premiere cep extensions

    for name in os.listdir(self.EXTENSIONS_PATH_REMOTE):
        log.debug("> name: {}".format(name))
        src = os.path.join(self.EXTENSIONS_PATH_REMOTE, name)
        dst = os.path.join(self.EXTENSIONS_PATH_LOCAL, name)
        process_pairs.append((name, src, dst))

    # synchronize all extensions
    for name, src, dst in process_pairs:
        if not os.path.isdir(src):
            continue
        if name not in _clearing_cache:
            continue
        if not os.path.exists(dst):
            os.makedirs(dst, mode=0o777)
        walktree(source=src, target=dst, options_input=["y", ">"])
        log.info("Extension {0} from `{1}` copied to `{2}`".format(
            name, src, dst
        ))
    # time.sleep(10)
    return


def clearing_caches_ui():
    '''Before every start of premiere it will make sure there is not
    outdated stuff in cep_cache dir'''

    if not os.path.isdir(self.EXTENSIONS_CACHE_PATH):
        os.makedirs(self.EXTENSIONS_CACHE_PATH, mode=0o777)
        log.info("Created dir: {}".format(self.EXTENSIONS_CACHE_PATH))

    for d in os.listdir(self.EXTENSIONS_CACHE_PATH):
        match = [p for p in _clearing_cache
                 if str(p) in d]

        if match:
            try:
                path = os.path.normpath(
                    os.path.join(self.EXTENSIONS_CACHE_PATH, d))
                log.info("Removing dir: {}".format(path))
                shutil.rmtree(path, ignore_errors=True)
            except Exception as e:
                log.error("problem: {}".format(e))


def test_rest_api_server(env):
    # from pprint import pformat
    rest_url = env.get("PYPE_REST_API_URL")
    project_name = "{AVALON_PROJECT}".format(**env)
    URL = "/".join((rest_url,
                    "avalon/projects",
                    project_name))
    log.debug("__ URL: {}".format(URL))
    try:
        req = requests.get(URL, data={}).text
        req_json = json.loads(req)
        # log.debug("_ req_json: {}".format(pformat(req_json)))
        log.debug("__ projectName: {}".format(req_json["data"]["name"]))
        assert req_json["data"]["name"] == project_name, (
            "Project data from Rest API server not correct")
        return True

    except Exception as e:
        message(title="Pype Rest API static server is not running ",
                message=("Before you can run Premiere, make sure "
                         "the system Tray Pype icon is running and "
                         "submenu `service` with name `Rest API` is "
                         "with green icon."
                         "\n Error: {}".format(e)),
                level="critical")
