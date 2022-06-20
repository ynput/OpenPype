import os

import pyblish.api
from openpype.lib.mongo import OpenPypeMongoConnection


class CollectShotgridEntities(pyblish.api.ContextPlugin):
    """Collect shotgrid entities according to the current context"""

    order = pyblish.api.CollectorOrder + 0.499
    label = "Shotgrid entities"

    def process(self, context):

        avalon_project = context.data.get("projectEntity")
        avalon_asset = context.data.get("assetEntity")
        avalon_task_name = os.getenv("AVALON_TASK")

        self.log.info(avalon_project)
        self.log.info(avalon_asset)

        sg_project = _get_shotgrid_project(context)
        sg_task = _get_shotgrid_task(
            avalon_project,
            avalon_asset,
            avalon_task_name
        )
        sg_entity = _get_shotgrid_entity(avalon_project, avalon_asset)

        if sg_project:
            context.data["shotgridProject"] = sg_project
            self.log.info(
                "Collected correspondig shotgrid project : {}".format(
                    sg_project
                )
            )

        if sg_task:
            context.data["shotgridTask"] = sg_task
            self.log.info(
                "Collected correspondig shotgrid task : {}".format(sg_task)
            )

        if sg_entity:
            context.data["shotgridEntity"] = sg_entity
            self.log.info(
                "Collected correspondig shotgrid entity : {}".format(sg_entity)
            )

    def _find_existing_version(self, code, context):

        filters = [
            ["project", "is", context.data.get("shotgridProject")],
            ["sg_task", "is", context.data.get("shotgridTask")],
            ["entity", "is", context.data.get("shotgridEntity")],
            ["code", "is", code],
        ]

        sg = context.data.get("shotgridSession")
        return sg.find_one("Version", filters, [])


def _get_shotgrid_collection(project):
    client = OpenPypeMongoConnection.get_mongo_client()
    return client.get_database("shotgrid_openpype").get_collection(project)


def _get_shotgrid_project(context):
    shotgrid_project_id = context.data["project_settings"].get(
        "shotgrid_project_id")
    if shotgrid_project_id:
        return {"type": "Project", "id": shotgrid_project_id}
    return {}


def _get_shotgrid_task(avalon_project, avalon_asset, avalon_task):
    sg_col = _get_shotgrid_collection(avalon_project["name"])
    shotgrid_task_hierarchy_row = sg_col.find_one(
        {
            "type": "Task",
            "_id": {"$regex": "^" + avalon_task + "_[0-9]*"},
            "parent": {"$regex": ".*," + avalon_asset["name"] + ","},
        }
    )
    if shotgrid_task_hierarchy_row:
        return {"type": "Task", "id": shotgrid_task_hierarchy_row["src_id"]}
    return {}


def _get_shotgrid_entity(avalon_project, avalon_asset):
    sg_col = _get_shotgrid_collection(avalon_project["name"])
    shotgrid_entity_hierarchy_row = sg_col.find_one(
        {"_id": avalon_asset["name"]}
    )
    if shotgrid_entity_hierarchy_row:
        return {
            "type": shotgrid_entity_hierarchy_row["type"],
            "id": shotgrid_entity_hierarchy_row["src_id"],
        }
    return {}
