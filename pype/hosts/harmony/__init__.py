import os
import time

from avalon import api, harmony
import pyblish.api
from pype import lib


def ensure_scene_settings():
    fps = lib.get_asset()["data"]["fps"]
    frame_start = lib.get_asset()["data"]["frameStart"]
    frame_end = lib.get_asset()["data"]["frameEnd"]

    settings = {
        "setFrameRate": fps,
        "setStartFrame": frame_start,
        "setStopFrame": frame_end
    }
    func = """function func(arg)
    {{
        scene.{method}(arg);
    }}
    func
    """
    for key, value in settings.items():
        if value is None:
            continue

        # Need to wait to not spam Harmony with multiple requests at the same
        # time.
        time.sleep(1)

        harmony.send({"function": func.format(method=key), "args": [value]})

    time.sleep(1)

    func = """function func(arg)
    {
        frame.remove(arg, frame.numberOf() - arg);
    }
    func
    """
    harmony.send({"function": func, "args": [frame_end]})


def install():
    print("Installing Pype config...")

    plugins_directory = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "plugins",
        "harmony"
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

    # Register callbacks.
    pyblish.api.register_callback(
        "instanceToggled", on_pyblish_instance_toggled
    )

    api.on("application.launched", ensure_scene_settings)


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
