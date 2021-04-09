import os
import logging

from avalon.tvpaint.communication_server import register_localization_file
from avalon.tvpaint import pipeline, lib
import pype.lib
import avalon.api
import avalon.io
import pyblish.api

from openpype.hosts import tvpaint

log = logging.getLogger(__name__)

HOST_DIR = os.path.dirname(os.path.abspath(tvpaint.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")


def on_instance_toggle(instance, old_value, new_value):
    instance_id = instance.data["uuid"]
    found_idx = None
    current_instances = pipeline.list_instances()
    for idx, workfile_instance in enumerate(current_instances):
        if workfile_instance["uuid"] == instance_id:
            found_idx = idx
            break

    if found_idx is None:
        return

    if "active" in current_instances[found_idx]:
        current_instances[found_idx]["active"] = new_value
        pipeline._write_instances(current_instances)


def application_launch():
    # Setup project settings if its the template that's launched.
    if "PYPE_TVPAINT_LAUNCHED_TEMPLATE_FILE" in os.environ:
        print("Setting up project...")

        project_doc = avalon.io.find_one({"type": "project"})
        project_data = project_doc["data"]
        asset_data = pype.lib.get_asset()["data"]

        framerate = asset_data.get("fps", project_data.get("fps", 25))

        width_key = "resolutionWidth"
        height_key = "resolutionHeight"
        width = asset_data.get(width_key, project_data.get(width_key, 1920))
        height = asset_data.get(height_key, project_data.get(height_key, 1080))

        lib.execute_george("tv_resizepage {} {} 0".format(width, height))
        lib.execute_george("tv_framerate {} \"timestretch\"".format(framerate))

        frame_start = asset_data.get("frameStart")
        frame_end = asset_data.get("frameEnd")

        handles = asset_data.get("handles") or 0
        handle_start = asset_data.get("handleStart")
        if handle_start is None:
            handle_start = handles

        handle_end = asset_data.get("handleEnd")
        if handle_end is None:
            handle_end = handles

        frame_start -= int(handle_start)
        frame_end += int(handle_end)

        lib.execute_george("tv_markin {} set".format(frame_start - 1))
        lib.execute_george("tv_markout {} set".format(frame_end - 1))


def install():
    log.info("OpenPype - Installing TVPaint integration")
    localization_file = os.path.join(HOST_DIR, "resources", "avalon.loc")
    register_localization_file(localization_file)

    pyblish.api.register_plugin_path(PUBLISH_PATH)
    avalon.api.register_plugin_path(avalon.api.Loader, LOAD_PATH)
    avalon.api.register_plugin_path(avalon.api.Creator, CREATE_PATH)

    registered_callbacks = (
        pyblish.api.registered_callbacks().get("instanceToggled") or []
    )
    if on_instance_toggle not in registered_callbacks:
        pyblish.api.register_callback("instanceToggled", on_instance_toggle)

    avalon.api.on("application.launched", application_launch)


def uninstall():
    log.info("OpenPype - Uninstalling TVPaint integration")
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    avalon.api.deregister_plugin_path(avalon.api.Loader, LOAD_PATH)
    avalon.api.deregister_plugin_path(avalon.api.Creator, CREATE_PATH)
