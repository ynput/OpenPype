import os
import sys

import pype
import pyblish.api


def main(env):
    from avalon.tools import publish
    # Registers pype's Global pyblish plugins
    pype.install()

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
