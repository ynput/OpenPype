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
        zou_asset_data = asset_data.get("zou")
        if not zou_asset_data:
            raise AssertionError("Zou asset data not found in OpenPype!")
        self.log.debug("Collected zou asset data: {}".format(zou_asset_data))

        zou_task_data = asset_data["tasks"][
            os.environ["AVALON_TASK"]].get("zou")
        if not zou_task_data:
            self.log.warning("Zou task data not found in OpenPype!")
        self.log.debug("Collected zou task data: {}".format(zou_task_data))

        kitsu_project = gazu.project.get_project(zou_asset_data["project_id"])
        if not kitsu_project:
            raise AssertionError("Project not found in kitsu!")
        context.data["kitsu_project"] = kitsu_project
        self.log.debug("Collect kitsu project: {}".format(kitsu_project))

        kitsu_asset = gazu.asset.get_asset(zou_asset_data["id"])
        if not kitsu_asset:
            raise AssertionError("Asset not found in kitsu!")
        context.data["kitsu_asset"] = kitsu_asset
        self.log.debug("Collect kitsu asset: {}".format(kitsu_asset))

        if zou_task_data:
            kitsu_task = gazu.task.get_task(zou_task_data["id"])
            if not kitsu_task:
                raise AssertionError("Task not found in kitsu!")
            context.data["kitsu_task"] = kitsu_task
            self.log.debug("Collect kitsu task: {}".format(kitsu_task))

        else:
            kitsu_task_type = gazu.task.get_task_type_by_name(
                os.environ["AVALON_TASK"]
            )
            if not kitsu_task_type:
                raise AssertionError(
                    "Task type {} not found in Kitsu!".format(
                        os.environ["AVALON_TASK"]
                    )
                )

            kitsu_task = gazu.task.get_task_by_name(
                kitsu_asset,
                kitsu_task_type
            )
            if not kitsu_task:
                raise AssertionError("Task not found in kitsu!")
            context.data["kitsu_task"] = kitsu_task
            self.log.debug("Collect kitsu task: {}".format(kitsu_task))
