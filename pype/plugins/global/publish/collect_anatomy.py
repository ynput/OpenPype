"""Collect Anatomy and global anatomy data.

Requires:
    session -> AVALON_TASK
    projectEntity, assetEntity -> collect_avalon_entities *(pyblish.api.CollectorOrder)
    username -> collect_pype_user *(pyblish.api.CollectorOrder + 0.001)
    datetimeData -> collect_datetime_data *(pyblish.api.CollectorOrder)

Provides:
    context -> anatomy (pypeapp.Anatomy)
    context -> anatomyData
"""

import os
import json

from avalon import api, lib
from pypeapp import Anatomy
import pyblish.api


class CollectAnatomy(pyblish.api.ContextPlugin):
    """Collect Anatomy into Context"""

    order = pyblish.api.CollectorOrder + 0.002
    label = "Collect Anatomy"

    def process(self, context):
        task_name = api.Session["AVALON_TASK"]

        project_entity = context.data["projectEntity"]
        asset_entity = context.data["assetEntity"]

        project_name = project_entity["name"]

        context.data["anatomy"] = Anatomy(project_name)
        self.log.info(
            "Anatomy object collected for project \"{}\".".format(project_name)
        )

        hierarchy_items = asset_entity["data"]["parents"]
        hierarchy = ""
        if hierarchy_items:
            hierarchy = os.path.join(*hierarchy_items)

        context_data = {
            "project": {
                "name": project_name,
                "code": project_entity["data"].get("code")
            },
            "asset": asset_entity["name"],
            "hierarchy": hierarchy.replace("\\", "/"),
            "task": task_name,

            "username": context.data["user"]
        }

        avalon_app_name = os.environ.get("AVALON_APP_NAME")
        if avalon_app_name:
            application_def = lib.get_application(avalon_app_name)
            app_dir = application_def.get("application_dir")
            if app_dir:
                context_data["app"] = app_dir

        datetime_data = context.data.get("datetimeData") or {}
        context_data.update(datetime_data)

        context.data["anatomyData"] = context_data

        self.log.info("Global anatomy Data collected")
        self.log.debug(json.dumps(context_data, indent=4))
