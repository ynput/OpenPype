import os
import sys
import logging

from avalon import io
from avalon import api as avalon
from avalon.vendor import Qt
from openpype import lib, api
import pyblish.api as pyblish
import openpype.hosts.aftereffects


log = logging.getLogger("openpype.hosts.aftereffects")


HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.aftereffects.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


def check_inventory():
    if not lib.any_outdated():
        return

    host = pyblish.registered_host()
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

    pyblish.register_plugin_path(PUBLISH_PATH)
    avalon.register_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.register_plugin_path(avalon.Creator, CREATE_PATH)
    log.info(PUBLISH_PATH)

    pyblish.register_callback(
        "instanceToggled", on_pyblish_instance_toggled
    )

    avalon.on("application.launched", application_launch)


def uninstall():
    pyblish.deregister_plugin_path(PUBLISH_PATH)
    avalon.deregister_plugin_path(avalon.Loader, LOAD_PATH)
    avalon.deregister_plugin_path(avalon.Creator, CREATE_PATH)


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
    duration = frame_end + handle_end - min(frame_start - handle_start, 0)
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
            api.get_current_project_settings()
            ["plugins"]
            ["aftereffects"]
            ["publish"]
            ["ValidateSceneSettings"]
            ["skip_resolution_check"]
        )
        skip_timelines_check = (
            api.get_current_project_settings()
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
