# -*- coding: utf-8 -*-
"""Pype Harmony Host implementation."""
import os
from pathlib import Path
import logging

from openpype import lib
from openpype.api import (get_current_project_settings)
import openpype.hosts.harmony

import pyblish.api

from avalon import io, harmony
import avalon.api
import avalon.tools.sceneinventory


log = logging.getLogger("openpype.hosts.harmony")

HOST_DIR = os.path.dirname(os.path.abspath(openpype.hosts.harmony.__file__))
PLUGINS_DIR = os.path.join(HOST_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")


def set_scene_settings(settings):
    """Set correct scene settings in Harmony.

    Args:
        settings (dict): Scene settings.

    Returns:
        dict: Dictionary of settings to set.

    """
    harmony.send(
        {"function": "PypeHarmony.setSceneSettings", "args": settings})


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
    entity_type = asset_data.get("entityType")

    scene_data = {
        "fps": fps,
        "frameStart": frame_start,
        "frameEnd": frame_end,
        "handleStart": handle_start,
        "handleEnd": handle_end,
        "resolutionWidth": resolution_width,
        "resolutionHeight": resolution_height
    }
    settings = get_current_project_settings()

    try:
        skip_resolution_check = \
            settings["harmony"]["general"]["skip_resolution_check"]
        skip_timelines_check = \
            settings["harmony"]["general"]["skip_timelines_check"]
    except KeyError:
        skip_resolution_check = []
        skip_timelines_check = []

    if os.getenv('AVALON_TASK') in skip_resolution_check:
        scene_data.pop("resolutionWidth")
        scene_data.pop("resolutionHeight")

    if entity_type in skip_timelines_check:
        scene_data.pop('frameStart', None)
        scene_data.pop('frameEnd', None)

    return scene_data


def ensure_scene_settings():
    """Validate if Harmony scene has valid settings."""
    settings = get_asset_settings()

    invalid_settings = []
    valid_settings = {}
    for key, value in settings.items():
        if value is None:
            invalid_settings.append(key)
        else:
            valid_settings[key] = value

    # Warn about missing attributes.
    if invalid_settings:
        msg = "Missing attributes:"
        for item in invalid_settings:
            msg += f"\n{item}"

        harmony.send(
            {"function": "PypeHarmony.message", "args": msg})

    set_scene_settings(valid_settings)


def check_inventory():
    """Check is scene contains outdated containers.

    If it does it will colorize outdated nodes and display warning message
    in Harmony.
    """
    if not lib.any_outdated():
        return

    host = avalon.api.registered_host()
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

    # Colour nodes.
    outdated_nodes = []
    for container in outdated_containers:
        if container["loader"] == "ImageSequenceLoader":
            outdated_nodes.append(
                harmony.find_node_by_name(container["name"], "READ")
            )
    harmony.send({"function": "PypeHarmony.setColor", "args": outdated_nodes})

    # Warn about outdated containers.
    msg = "There are outdated containers in the scene."
    harmony.send({"function": "PypeHarmony.message", "args": msg})


def application_launch():
    """Event that is executed after Harmony is launched."""
    # FIXME: This is breaking server <-> client communication.
    # It is now moved so it it manually called.
    # ensure_scene_settings()
    # check_inventory()
    # fills OPENPYPE_HARMONY_JS
    pype_harmony_path = Path(__file__).parent.parent / "js" / "PypeHarmony.js"
    pype_harmony_js = pype_harmony_path.read_text()

    # go through js/creators, loaders and publish folders and load all scripts
    script = ""
    for item in ["creators", "loaders", "publish"]:
        dir_to_scan = Path(__file__).parent.parent / "js" / item
        for child in dir_to_scan.iterdir():
            script += child.read_text()

    # send scripts to Harmony
    harmony.send({"script": pype_harmony_js})
    harmony.send({"script": script})


def export_template(backdrops, nodes, filepath):
    """Export Template to file.

    Args:
        backdrops (list): List of backdrops to export.
        nodes (list): List of nodes to export.
        filepath (str): Path where to save Template.

    """
    harmony.send({
        "function": "PypeHarmony.exportTemplate",
        "args": [
            backdrops,
            nodes,
            os.path.basename(filepath),
            os.path.dirname(filepath)
        ]
    })


def install():
    """Install Pype as host config."""
    print("Installing Pype config ...")

    pyblish.api.register_plugin_path(PUBLISH_PATH)
    avalon.api.register_plugin_path(avalon.api.Loader, LOAD_PATH)
    avalon.api.register_plugin_path(avalon.api.Creator, CREATE_PATH)
    log.info(PUBLISH_PATH)

    # Register callbacks.
    pyblish.api.register_callback(
        "instanceToggled", on_pyblish_instance_toggled
    )

    avalon.api.on("application.launched", application_launch)


def uninstall():
    pyblish.api.deregister_plugin_path(PUBLISH_PATH)
    avalon.api.deregister_plugin_path(avalon.api.Loader, LOAD_PATH)
    avalon.api.deregister_plugin_path(avalon.api.Creator, CREATE_PATH)


def on_pyblish_instance_toggled(instance, old_value, new_value):
    """Toggle node enabling on instance toggles."""
    node = None
    if instance.data.get("setMembers"):
        node = instance.data["setMembers"][0]

    if node:
        harmony.send(
            {
                "function": "PypeHarmony.toggleInstance",
                "args": [node, new_value]
            }
        )
