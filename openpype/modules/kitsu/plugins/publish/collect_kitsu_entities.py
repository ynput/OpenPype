# -*- coding: utf-8 -*-
import gazu
import pyblish.api


class CollectKitsuEntities(pyblish.api.ContextPlugin):
    """Collect Kitsu entities according to the current context"""

    order = pyblish.api.CollectorOrder + 0.499
    label = "Kitsu entities"

    def process(self, context):

        kitsu_project = None

        kitsu_entities_by_id = {}
        for instance in context:
            asset_doc = instance.data.get("assetEntity")
            task_name = instance.data.get("task")
            if not asset_doc:
                continue

            zou_asset_data = asset_doc["data"].get("zou")
            if not zou_asset_data:
                raise ValueError("Zou asset data not found in OpenPype!")

            if kitsu_project is None:
                kitsu_project = gazu.project.get_project(
                    zou_asset_data["project_id"])
                if not kitsu_project:
                    raise ValueError("Project not found in kitsu!")

            entity_type = zou_asset_data["type"]
            kitsu_id = zou_asset_data["id"]
            kitsu_entity = kitsu_entities_by_id.get(kitsu_id)
            if not kitsu_entity:
                if entity_type == "Shot":
                    kitsu_entity = gazu.shot.get_shot(kitsu_id)
                else:
                    kitsu_entity = gazu.asset.get_asset(kitsu_id)
                kitsu_entities_by_id[kitsu_id] = kitsu_entity

            if not kitsu_entity:
                raise ValueError(
                    "{} not found in kitsu!".format(entity_type))
            instance.data["kitsu_entity"] = kitsu_entity

            if not task_name:
                continue
            zou_task_data = asset_doc["data"]["tasks"][task_name].get("zou")
            self.log.debug(
                "Collected zou task data: {}".format(zou_task_data))
            if not zou_task_data:
                kitsu_task_type = gazu.task.get_task_type_by_name(task_name)
                if not kitsu_task_type:
                    raise ValueError(
                        "Task type {} not found in Kitsu!".format(task_name)
                    )
                continue
            kitsu_task_id = zou_task_data["id"]
            kitsu_task = kitsu_entities_by_id.get(kitsu_task_id)
            if not kitsu_task:
                kitsu_task = gazu.task.get_task(zou_task_data["id"])
                kitsu_entities_by_id[kitsu_task_id] = kitsu_task

            if not kitsu_task:
                raise ValueError("Task not found in kitsu!")
            instance.data["kitsu_task"] = kitsu_task
            self.log.debug("Collect kitsu task: {}".format(kitsu_task))

        context.data["kitsu_project"] = kitsu_project
