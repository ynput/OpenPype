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
import pyblish.api

from openpype.pipeline.template_data import get_template_data


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
        "user": "MeDespicable",
        # Duplicated entry
        "username": "MeDespicable",

        # Current host name
        "app": "maya"

        *** OPTIONAL ***
        + mutliple keys from `datetimeData` (See it's collector)
    }
    """

    order = pyblish.api.CollectorOrder + 0.002
    label = "Collect Anatomy Context Data"

    def process(self, context):
        host_name = context.data["hostName"]
        system_settings = context.data["system_settings"]
        project_entity = context.data["projectEntity"]
        asset_entity = context.data.get("assetEntity")
        task_name = None
        if asset_entity:
            task_name = context.data["task"]

        anatomy_data = get_template_data(
            project_entity, asset_entity, task_name, host_name, system_settings
        )
        anatomy_data.update(context.data.get("datetimeData") or {})

        username = context.data["user"]
        anatomy_data["user"] = username
        # Backwards compatibility for 'username' key
        anatomy_data["username"] = username

        # Store
        context.data["anatomyData"] = anatomy_data

        self.log.debug("Global Anatomy Context Data collected:\n{}".format(
            json.dumps(anatomy_data, indent=4)
        ))
