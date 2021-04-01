import os
import sys

import openpype
import pyblish.api


def main(env):
    from avalon.tools import publish
    # Registers pype's Global pyblish plugins
    openpype.install()

    # Register additional paths
    addition_paths_str = env.get("PUBLISH_PATHS") or ""
    addition_paths = addition_paths_str.split(os.pathsep)
    for path in addition_paths:
        path = os.path.normpath(path)
        if not os.path.exists(path):
            continue
        pyblish.api.register_plugin_path(path)

    return publish.show()


if __name__ == "__main__":
    result = main(os.environ)
    sys.exit(not bool(result))
