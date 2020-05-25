import os
import sys
import shutil

from avalon import api
from pype.widgets.message_window import message
from pypeapp import Logger

log = Logger().get_logger(__name__, "resolve")

self = sys.modules[__name__]

AVALON_CONFIG = os.environ["AVALON_CONFIG"]
PARENT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.dirname(PARENT_DIR)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins")

self.UTILITY_SCRIPTS = os.path.join(PARENT_DIR, "resolve_utility_scripts")

self.PUBLISH_PATH = os.path.join(
    PLUGINS_DIR, "resolve", "publish"
).replace("\\", "/")

if os.getenv("PUBLISH_PATH", None):
    if self.PUBLISH_PATH not in os.environ["PUBLISH_PATH"]:
        os.environ["PUBLISH_PATH"] = os.pathsep.join(
            os.environ["PUBLISH_PATH"].split(os.pathsep) +
            [self.PUBLISH_PATH]
        )
else:
    os.environ["PUBLISH_PATH"] = self.PUBLISH_PATH


def ls():
    pass


def sync_utility_scripts(env=None):
    """ Synchronizing basic utlility scripts for resolve.

    To be able to run scripts from inside `Resolve/Workspace/Scripts` menu
    all scripts has to be accessible from defined folder.
    """
    if not env:
        env = os.environ

    us_dir = env.get("RESOLVE_UTILITY_SCRIPTS_DIR", "")
    scripts = os.listdir(self.UTILITY_SCRIPTS)

    log.info(f"Utility Scripts Dir: `{self.UTILITY_SCRIPTS}`")
    log.info(f"Utility Scripts: `{scripts}`")

    # make sure no script file is in folder
    if next((s for s in os.listdir(us_dir)), None):
        for s in os.listdir(us_dir):
            path = os.path.join(us_dir, s)
            log.info(f"Removing `{path}`...")
            os.remove(path)

    # copy scripts into Resolve's utility scripts dir
    for s in scripts:
        src = os.path.join(self.UTILITY_SCRIPTS, s)
        dst = os.path.join(us_dir, s)
        log.info(f"Copying `{src}` to `{dst}`...")
        shutil.copy2(src, dst)


def reload_pipeline():
    """Attempt to reload pipeline at run-time.

    CAUTION: This is primarily for development and debugging purposes.

    """

    import importlib
    import pype.resolve

    api.uninstall()

    for module in ("avalon.io",
                   "avalon.lib",
                   "avalon.pipeline",
                   "avalon.api",
                   "avalon.tools",

                   "{}".format(AVALON_CONFIG),
                   "{}.resolve".format(AVALON_CONFIG),
                   "{}.resolve.lib".format(AVALON_CONFIG)
                   ):
        log.info("Reloading module: {}...".format(module))
        try:
            module = importlib.import_module(module)
            importlib.reload(module)
        except Exception as e:
            log.warning("Cannot reload module: {}".format(e))

    api.install(pype.resolve)


def setup(env=None):
    """ Running wrapper
    """
    if not env:
        env = os.environ

    # synchronize resolve utility scripts
    sync_utility_scripts(env)

    log.info("Resolve Pype wrapper has been installed")
