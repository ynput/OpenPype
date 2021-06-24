import os
import sys

from avalon import api, io
from avalon.vendor import Qt
from pype import lib
import pyblish.api
from pype.api import config


def check_inventory():
    if not lib.any_outdated():
        return

    host = api.registered_host()
    outdated_containers = []
    for container in host.ls():
        representation = container['representation']
        representation_doc = io.find_one(
            {
                "_id": io.ObjectId(representation),
                "type": "representation"
            },
            projection={"parent": True}
        )
        if representation_doc and not lib.is_latest(representation_doc):
            outdated_containers.append(container)

    # Warn about outdated containers.
    print("Starting new QApplication..")
    app = Qt.QtWidgets.QApplication(sys.argv)

    message_box = Qt.QtWidgets.QMessageBox()
    message_box.setIcon(Qt.QtWidgets.QMessageBox.Warning)
    msg = "There are outdated containers in the scene."
    message_box.setText(msg)
    message_box.exec_()

    # Garbage collect QApplication.
    del app


def application_launch():
    check_inventory()


def install():
    print("Installing Pype config...")

    plugins_directory = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "plugins",
        "aftereffects"
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

    api.on("application.launched", application_launch)


def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle layer visibility on instance toggles."""
    instance[0].Visible = new_value


def get_asset_settings():
    """Get settings on current asset from database.

    Returns:
        dict: Scene data.

    """
    asset_data = lib.get_asset()["data"]
    fps = asset_data.get("fps")
    frame_start = asset_data.get("frameStart")
    frame_end = asset_data.get("frameEnd")
    handle_start = asset_data.get("handleStart")
    handle_end = asset_data.get("handleEnd")
    resolution_width = asset_data.get("resolutionWidth")
    resolution_height = asset_data.get("resolutionHeight")
    duration = (frame_end - frame_start + 1) + handle_start + handle_end
    entity_type = asset_data.get("entityType")

    scene_data = {
        "fps": fps,
        "frameStart": frame_start,
        "frameEnd": frame_end,
        "handleStart": handle_start,
        "handleEnd": handle_end,
        "resolutionWidth": resolution_width,
        "resolutionHeight": resolution_height,
        "duration": duration
    }

    try:
        # temporary, in pype3 replace with api.get_current_project_settings
        skip_resolution_check = (
            get_current_project_settings()
            ["plugins"]
            ["aftereffects"]
            ["publish"]
            ["ValidateSceneSettings"]
            ["skip_resolution_check"]
        )
        skip_timelines_check = (
            get_current_project_settings()
            ["plugins"]
            ["aftereffects"]
            ["publish"]
            ["ValidateSceneSettings"]
            ["skip_timelines_check"]
        )
    except KeyError:
        skip_resolution_check = ['*']
        skip_timelines_check = ['*']

    if os.getenv('AVALON_TASK') in skip_resolution_check or \
            '*' in skip_timelines_check:
        scene_data.pop("resolutionWidth")
        scene_data.pop("resolutionHeight")

    if entity_type in skip_timelines_check or '*' in skip_timelines_check:
        scene_data.pop('fps', None)
        scene_data.pop('frameStart', None)
        scene_data.pop('frameEnd', None)
        scene_data.pop('handleStart', None)
        scene_data.pop('handleEnd', None)

    return scene_data


# temporary, in pype3 replace with api.get_current_project_settings
def get_current_project_settings():
    """Project settings for current context project.

    Project name should be stored in environment variable `AVALON_PROJECT`.
    This function should be used only in host context where environment
    variable must be set and should not happen that any part of process will
    change the value of the enviornment variable.
    """
    project_name = os.environ.get("AVALON_PROJECT")
    if not project_name:
        raise ValueError(
            "Missing context project in environemt variable `AVALON_PROJECT`."
        )
    presets = config.get_presets(project=os.environ['AVALON_PROJECT'])
    return presets
