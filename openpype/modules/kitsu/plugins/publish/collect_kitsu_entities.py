import os

import gazu

import pyblish.api


class CollectKitsuEntities(pyblish.api.ContextPlugin):
    """Collect Kitsu entities according to the current context"""

    order = pyblish.api.CollectorOrder + 0.499
    label = "Kitsu entities"

    def process(self, context):

        os.environ["AVALON_PROJECT"],
        os.environ["AVALON_ASSET"],
        os.environ["AVALON_TASK"],
        os.environ["AVALON_APP_NAME"]

        asset_data = context.data["assetEntity"]["data"]
        zoo_asset_data = asset_data.get("zou")
        if not zoo_asset_data:
            raise

        kitsu_project = gazu.project.get_project(zoo_asset_data["project_id"])
        if not kitsu_project:
            raise
        context.data["kitsu_project"] = kitsu_project

        kitsu_asset = gazu.asset.get_asset(zoo_asset_data["entity_type_id"])
        if not kitsu_asset:
            raise
        context.data["kitsu_asset"] = kitsu_asset

        # kitsu_task_type = gazu.task.get_task_type_by_name(instance.data["task"])
        # if not kitsu_task_type:
        #     raise
        # context.data["kitsu_task_type"] = kitsu_task_type

        zoo_task_data = asset_data["tasks"][os.environ["AVALON_TASK"]].get("zou")
        kitsu_task = gazu.task.get_task(
            asset_data["zou"],
            kitsu_task_type
        )
        if not kitsu_task:
            raise
        context.data["kitsu_task"] = kitsu_task

        wip = gazu.task.get_task_status_by_short_name("wip")

        task = gazu.task.get_task_by_name(asset, modeling)
        comment = gazu.task.add_comment(task, wip, "Change status to work in progress")

        person = gazu.person.get_person_by_desktop_login("john.doe")

        # task_type = gazu.task.get_task_type_by_name(instance.data["task"])

        # entity_task = gazu.task.get_task_by_entity(
        #     asset_data["zou"],
        #     task_type
        # )

        raise