"""Collect global context Anatomy data.

Requires:
    context -> anatomy
    context -> projectEntity
    context -> assetEntity
    context -> username
    context -> datetimeData
    session -> AVALON_TASK

Provides:
    context -> anatomyData
"""

import os
import json

from openpype.lib import ApplicationManager
from avalon import api, lib
import pyblish.api


class CollectAnatomyContextData(pyblish.api.ContextPlugin):
    """Collect Anatomy Context data.

    Example:
    context.data["anatomyData"] = {
        "project": {
            "name": "MyProject",
            "code": "myproj"
        },
        "asset": "AssetName",
        "hierarchy": "path/to/asset",
        "task": "Working",
        "username": "MeDespicable",

        *** OPTIONAL ***
        "app": "maya"       # Current application base name
        + mutliple keys from `datetimeData`         # see it's collector
    }
    """

    order = pyblish.api.CollectorOrder + 0.002
    label = "Collect Anatomy Context Data"

    def process(self, context):
        task_name = api.Session["AVALON_TASK"]

        project_entity = context.data["projectEntity"]
        asset_entity = context.data["assetEntity"]

        hierarchy_items = asset_entity["data"]["parents"]
        hierarchy = ""
        if hierarchy_items:
            hierarchy = os.path.join(*hierarchy_items)

        frame_start = asset_entity["data"]["frameStart"]
        frame_end = asset_entity["data"]["frameEnd"]

        context_data = {
            "project": {
                "name": project_entity["name"],
                "code": project_entity["data"].get("code")
            },
            "asset": asset_entity["name"],
            "hierarchy": hierarchy.replace("\\", "/"),
            "task": task_name,
            "username": context.data["user"],
            "app": context.data["hostName"],
            "frame_start": frame_start,
            "frame_duration": int(frame_end - frame_start + 1),
            "frame_end": frame_end
        }

        datetime_data = context.data.get("datetimeData") or {}
        context_data.update(datetime_data)

        context.data["anatomyData"] = context_data

        self.log.info("Global anatomy Data collected")
        self.log.debug(json.dumps(context_data, indent=4))
