import os

from avalon import api, harmony
import pyblish.api


def install():
    print("Installing Pype config...")

    plugins_directory = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "plugins", "harmony"
    )

    pyblish.api.register_plugin_path(
        os.path.join(plugins_directory, "publish")
    )
    api.register_plugin_path(
        api.Loader, os.path.join(plugins_directory, "load")
    )
    api.register_plugin_path(
        api.Creator, os.path.join(plugins_directory, "create")
    )

    pyblish.api.register_callback(
        "instanceToggled", on_pyblish_instance_toggled
    )


def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle node enabling on instance toggles."""
    func = """function func(args)
    {
        node.setEnable(args[0], args[1])
    }
    func
    """
    harmony.send(
        {"function": func, "args": [instance[0], new_value]}
    )
