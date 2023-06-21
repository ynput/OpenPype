# -*- coding: utf-8 -*-
import gazu
import pyblish.api


class CollectKitsuEntities(pyblish.api.ContextPlugin):
    """Collect Kitsu entities according to the current context"""

    order = pyblish.api.CollectorOrder + 0.499
    label = "Kitsu entities"

    def process(self, context):
        kitsu_project = gazu.project.get_project_by_name(
            context.data["projectName"]
        )
        if not kitsu_project:
            raise ValueError("Project not found in kitsu!")

        context.data["kitsu_project"] = kitsu_project
        self.log.debug("Collect kitsu project: {}".format(kitsu_project))

        kitsu_entities_by_id = {}
        for instance in context:
            asset_doc = instance.data.get("assetEntity")
            if not asset_doc:
                continue

            zou_asset_data = asset_doc["data"].get("zou")
            if not zou_asset_data:
                raise ValueError("Zou asset data not found in OpenPype!")

            task_name = instance.data.get("task", context.data.get("task"))
            if not task_name:
                continue

            zou_task_data = asset_doc["data"]["tasks"][task_name].get("zou")
            self.log.debug(
                "Collected zou task data: {}".format(zou_task_data)
            )

            entity_id = zou_asset_data["id"]
            entity = kitsu_entities_by_id.get(entity_id)
            if not entity:
                entity = gazu.entity.get_entity(entity_id)
                if not entity:
                    raise ValueError(
                        "{} was not found in kitsu!".format(
                            zou_asset_data["name"]
                        )
                    )

            kitsu_entities_by_id[entity_id] = entity
            instance.data["entity"] = entity
            self.log.debug(
                "Collect kitsu {}: {}".format(zou_asset_data["type"], entity)
            )

            if zou_task_data:
                kitsu_task_id = zou_task_data["id"]
                kitsu_task = kitsu_entities_by_id.get(kitsu_task_id)
                if not kitsu_task:
                    kitsu_task = gazu.task.get_task(zou_task_data["id"])
                    kitsu_entities_by_id[kitsu_task_id] = kitsu_task
            else:
                kitsu_task_type = gazu.task.get_task_type_by_name(task_name)
                if not kitsu_task_type:
                    raise ValueError(
                        "Task type {} not found in Kitsu!".format(task_name)
                    )

                kitsu_task = gazu.task.get_task_by_name(
                    entity, kitsu_task_type
                )

            if not kitsu_task:
                raise ValueError("Task not found in kitsu!")
            instance.data["kitsu_task"] = kitsu_task
            self.log.debug("Collect kitsu task: {}".format(kitsu_task))
