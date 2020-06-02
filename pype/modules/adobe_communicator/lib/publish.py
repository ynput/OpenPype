import os
import sys
import pype
import importlib
import pyblish.api
import pyblish.util
import avalon.api
from avalon.tools import publish
from pype.api import Logger

log = Logger().get_logger(__name__)


def main(env):
    # Registers pype's Global pyblish plugins
    pype.install()

    # Register Host (and it's pyblish plugins)
    host_name = env["AVALON_APP"]
    # TODO not sure if use "pype." or "avalon." for host import
    host_import_str = f"pype.{host_name}"

    try:
        host_module = importlib.import_module(host_import_str)
    except ModuleNotFoundError:
        log.error((
            f"Host \"{host_name}\" can't be imported."
            f" Import string \"{host_import_str}\" failed."
        ))
        return False

    avalon.api.install(host_module)

    # Register additional paths
    addition_paths_str = env.get("PUBLISH_PATHS") or ""
    addition_paths = addition_paths_str.split(os.pathsep)
    for path in addition_paths:
        path = os.path.normpath(path)
        if not os.path.exists(path):
            continue

        pyblish.api.register_plugin_path(path)

    # Register project specific plugins
    project_name = os.environ["AVALON_PROJECT"]
    project_plugins_paths = env.get("PYPE_PROJECT_PLUGINS") or ""
    for path in project_plugins_paths.split(os.pathsep):
        plugin_path = os.path.join(path, project_name, "plugins")
        if os.path.exists(plugin_path):
            pyblish.api.register_plugin_path(plugin_path)

    return publish.show()


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
