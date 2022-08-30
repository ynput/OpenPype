import os
import sys

import pyblish.api
from openpype.pipeline import install_openpype_plugins
from openpype.tools.utils.host_tools import show_publish


def main(env):
    # Registers pype's Global pyblish plugins
    install_openpype_plugins()

    # Register additional paths
    addition_paths_str = env.get("PUBLISH_PATHS") or ""
    addition_paths = addition_paths_str.split(os.pathsep)
    for path in addition_paths:
        path = os.path.normpath(path)
        if not os.path.exists(path):
            continue
        pyblish.api.register_plugin_path(path)

    return show_publish()


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
