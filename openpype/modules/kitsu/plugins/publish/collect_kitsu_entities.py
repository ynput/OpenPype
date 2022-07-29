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

        zou_task_data = asset_data["tasks"][os.environ["AVALON_TASK"]].get(
            "zou"
        )
        if not zou_task_data:
            self.log.warning("Zou task data not found in OpenPype!")
        self.log.debug("Collected zou task data: {}".format(zou_task_data))

        kitsu_project = gazu.project.get_project(zou_asset_data["project_id"])
        if not kitsu_project:
            raise AssertionError("Project not found in kitsu!")
        context.data["kitsu_project"] = kitsu_project
        self.log.debug("Collect kitsu project: {}".format(kitsu_project))

        entity_type = zou_asset_data["type"]
        if entity_type == "Shot":
            kitsu_entity = gazu.shot.get_shot(zou_asset_data["id"])
        else:
            kitsu_entity = gazu.asset.get_asset(zou_asset_data["id"])

        if not kitsu_entity:
            raise AssertionError("{} not found in kitsu!".format(entity_type))

        context.data["kitsu_entity"] = kitsu_entity
        self.log.debug("Collect kitsu {}: {}".format(entity_type, kitsu_entity))

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
                kitsu_entity, kitsu_task_type
            )
            if not kitsu_task:
                raise AssertionError("Task not found in kitsu!")
            context.data["kitsu_task"] = kitsu_task
            self.log.debug("Collect kitsu task: {}".format(kitsu_task))
