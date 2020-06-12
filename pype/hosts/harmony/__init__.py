import os
import sys

from avalon import api, harmony
from avalon.vendor import Qt
import pyblish.api
from pype import lib


def ensure_scene_settings():
    asset_data = lib.get_asset()["data"]
    fps = asset_data["fps"]
    frame_start = asset_data["frameStart"]
    frame_end = asset_data["frameEnd"]
    resolution_width = asset_data.get("resolutionWidth")
    resolution_height = asset_data.get("resolutionHeight")

    settings = {
        "fps": fps,
        "frameStart": frame_start,
        "frameEnd": frame_end,
        "resolutionWidth": resolution_width,
        "resolutionHeight": resolution_height
    }

    invalid_settings = []
    valid_settings = {}
    for key, value in settings.items():
        if value is None:
            invalid_settings.append(key)
        else:
            valid_settings[key] = value

    # Warn about missing attributes.
    print("Starting new QApplication..")
    app = Qt.QtWidgets.QApplication(sys.argv)

    message_box = Qt.QtWidgets.QMessageBox()
    message_box.setIcon(Qt.QtWidgets.QMessageBox.Warning)
    msg = "Missing attributes:"
    if invalid_settings:
        for item in invalid_settings:
            msg += f"\n{item}"
        message_box.setText(msg)
        message_box.exec_()

    # Garbage collect QApplication.
    del app

    func = """function func(args)
    {
        if (args[0]["fps"])
        {
            scene.setFrameRate(args[0]["fps"]);
        }
        if (args[0]["frameStart"])
        {
            scene.setStartFrame(args[0]["frameStart"]);
        }
        if (args[0]["frameEnd"])
        {
            scene.setStopFrame(args[0]["frameEnd"]);
            frame.remove(
                args[0]["frameEnd"], frame.numberOf() - args[0]["frameEnd"]
            );
        }
        if (args[0]["resolutionWidth"] && args[0]["resolutionHeight"])
        {
            scene.setDefaultResolution(
                args[0]["resolutionWidth"], args[0]["resolutionHeight"], 41.112
            )
        }
    }
    func
    """
    harmony.send({"function": func, "args": [valid_settings]})


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
