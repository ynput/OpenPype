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

import json
from openpype.lib import (
    get_system_general_anatomy_data
)
from avalon import api
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
        project_entity = context.data["projectEntity"]
        context_data = {
            "project": {
                "name": project_entity["name"],
                "code": project_entity["data"].get("code")
            },
            "username": context.data["user"],
            "app": context.data["hostName"]
        }

        context.data["anatomyData"] = context_data

        # add system general settings anatomy data
        system_general_data = get_system_general_anatomy_data()
        context_data.update(system_general_data)

        datetime_data = context.data.get("datetimeData") or {}
        context_data.update(datetime_data)

        asset_entity = context.data.get("assetEntity")
        if asset_entity:
            task_name = api.Session["AVALON_TASK"]

            asset_tasks = asset_entity["data"]["tasks"]
            task_type = asset_tasks.get(task_name, {}).get("type")

            project_task_types = project_entity["config"]["tasks"]
            task_code = project_task_types.get(task_type, {}).get("short_name")

            asset_parents = asset_entity["data"]["parents"]
            hierarchy = "/".join(asset_parents)

            parent_name = project_entity["name"]
            if asset_parents:
                parent_name = asset_parents[-1]

            context_data.update({
                "asset": asset_entity["name"],
                "parent": parent_name,
                "hierarchy": hierarchy,
                "task": {
                    "name": task_name,
                    "type": task_type,
                    "short": task_code,
                }
            })

        intent = context.data.get("intent")
        if intent and isinstance(intent, dict):
            intent_value = intent.get("value")
            if intent_value:
                context_data["intent"] = intent_value

        self.log.info("Global anatomy Data collected")
        self.log.debug(json.dumps(context_data, indent=4))
