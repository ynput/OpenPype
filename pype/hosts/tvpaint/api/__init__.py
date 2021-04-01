import os
import logging

from avalon.tvpaint.communication_server import register_localization_file
from avalon.tvpaint import pipeline
import avalon.api
import pyblish.api

from openpype.hosts import tvpaint

log = logging.getLogger("pype.hosts.tvpaint")

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


def install():
    log.info("Pype - Installing TVPaint integration")
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


def uninstall():
    log.info("Pype - Uninstalling TVPaint integration")
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    avalon.api.deregister_plugin_path(avalon.api.Loader, LOAD_PATH)
    avalon.api.deregister_plugin_path(avalon.api.Creator, CREATE_PATH)
