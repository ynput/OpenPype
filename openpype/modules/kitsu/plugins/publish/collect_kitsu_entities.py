# -*- coding: utf-8 -*-
import os

import gazu
import pyblish.api

from openpype.client import (
    get_assets,
)


class CollectKitsuEntities(pyblish.api.ContextPlugin):
    """Collect Kitsu entities according to the current context"""

    order = pyblish.api.CollectorOrder + 0.499
    label = "Kitsu entities"

    def process(self, context):

        # Get all needed names
        project_name = context.data.get("projectName")
        asset_name = context.data.get("asset")
        task_name = context.data.get("task")
        # If asset and task name doesn't exist in context, look in instance
        for instance in context:
            if not asset_name:
                asset_name = instance.data.get("asset")
            if not task_name:
                task_name = instance.data.get("task")

        # Get all assets of the local project
        asset_docs = {
            asset_doc["name"]: asset_doc
            for asset_doc in get_assets(project_name)
        }

        # Get asset object
        asset = asset_docs.get(asset_name)
        if not asset:
            raise AssertionError(f"{asset_name} not found in DB")

        zou_asset_data = asset["data"].get("zou")
        if not zou_asset_data:
            raise AssertionError("Zou asset data not found in OpenPype!")
        self.log.debug(f"Collected zou asset data: {zou_asset_data}")

        kitsu_project = gazu.project.get_project(zou_asset_data["project_id"])
        if not kitsu_project:
            raise AssertionError("Project not found in kitsu!")
        context.data["kitsu_project"] = kitsu_project
        self.log.debug(f"Collect kitsu project: {kitsu_project}")

        entity_type = zou_asset_data["type"]
        if entity_type == "Shot":
            kitsu_entity = gazu.shot.get_shot(zou_asset_data["id"])
        else:
            kitsu_entity = gazu.asset.get_asset(zou_asset_data["id"])
        if not kitsu_entity:
            raise AssertionError(f"{entity_type} not found in kitsu!")
        context.data["kitsu_entity"] = kitsu_entity
        self.log.debug(f"Collect kitsu {entity_type}: {kitsu_entity}")

        if task_name:
            zou_task_data = asset["data"]["tasks"][task_name].get("zou")
            self.log.debug(f"Collected zou task data: {zou_task_data}")
            if zou_task_data:
                kitsu_task = gazu.task.get_task(zou_task_data["id"])
                if not kitsu_task:
                    raise AssertionError("Task not found in kitsu!")
                context.data["kitsu_task"] = kitsu_task
                self.log.debug(f"Collect kitsu task: {kitsu_task}")
            else:
                kitsu_task_type = gazu.task.get_task_type_by_name(task_name)
                if not kitsu_task_type:
                    raise AssertionError(
                        f"Task type {task_name} not found in Kitsu!"
                    )

                kitsu_task = gazu.task.get_task_by_name(
                    kitsu_entity, kitsu_task_type
                )
                if not kitsu_task:
                    raise AssertionError("Task not found in kitsu!")
                context.data["kitsu_task"] = kitsu_task
                self.log.debug(f"Collect kitsu task: {kitsu_task}")
