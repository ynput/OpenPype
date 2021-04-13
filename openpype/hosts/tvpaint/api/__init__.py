import os
import logging

import avalon.api
import pyblish.api
from avalon.tvpaint import pipeline
from avalon.tvpaint.communication_server import register_localization_file
from .lib import set_context_settings

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


def initial_launch():
    # Setup project settings if its the template that's launched.
    # TODO also check for template creation when it's possible to define
    #   templates
    last_workfile = os.environ.get("AVALON_LAST_WORKFILE")
    if not last_workfile or os.path.exists(last_workfile):
        return

    log.info("Setting up project...")
    set_context_settings()


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

    avalon.api.on("application.launched", initial_launch)


def uninstall():
    log.info("OpenPype - Uninstalling TVPaint integration")
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    avalon.api.deregister_plugin_path(avalon.api.Loader, LOAD_PATH)
    avalon.api.deregister_plugin_path(avalon.api.Creator, CREATE_PATH)
