# -*- coding: utf-8 -*-
import os

import gazu
import pyblish.api


class CollectKitsuEntities(pyblish.api.ContextPlugin):
    """Collect Kitsu entities according to the current context"""

    order = pyblish.api.CollectorOrder + 0.499
    label = "Kitsu entities"

    def process(self, context):

        asset_data = context.data["assetEntity"]["data"]
        zoo_asset_data = asset_data.get("zou")
        if not zoo_asset_data:
            raise AssertionError("Zoo asset data not found in OpenPype!")
        self.log.debug("Collected zoo asset data: {}".format(zoo_asset_data))

        zoo_task_data = asset_data["tasks"][os.environ["AVALON_TASK"]].get("zou")
        if not zoo_task_data:
            raise AssertionError("Zoo task data not found in OpenPype!")
        self.log.debug("Collected zoo task data: {}".format(zoo_task_data))

        kitsu_project = gazu.project.get_project(zoo_asset_data["project_id"])
        if not kitsu_project:
            raise AssertionError("Project not not found in kitsu!")
        context.data["kitsu_project"] = kitsu_project
        self.log.debug("Collect kitsu project: {}".format(kitsu_project))

        kitsu_asset = gazu.asset.get_asset(zoo_asset_data["id"])
        if not kitsu_asset:
            raise AssertionError("Asset not not found in kitsu!")
        context.data["kitsu_asset"] = kitsu_asset
        self.log.debug("Collect kitsu asset: {}".format(kitsu_asset))

        kitsu_task = gazu.task.get_task(zoo_task_data["id"]) 
        if not kitsu_task:
            raise AssertionError("Task not not found in kitsu!")
        context.data["kitsu_task"] = kitsu_task
        self.log.debug("Collect kitsu task: {}".format(kitsu_task))
