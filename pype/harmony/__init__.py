import os

import avalon.api
import pyblish.api


def install():
    print("Installing Pype config...")

    plugins_directory = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "plugins", "harmony"
    )

    pyblish.api.register_plugin_path(
        os.path.join(plugins_directory, "publish")
    )
    avalon.api.register_plugin_path(
        avalon.api.Loader, os.path.join(plugins_directory, "load")
    )
    avalon.api.register_plugin_path(
        avalon.api.Creator, os.path.join(plugins_directory, "create")
    )
