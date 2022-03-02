from typing import Dict, List

from pymongo import UpdateOne
from pymongo.collection import Collection

from avalon.api import AvalonMongoDB
from openpype.lib import create_project


def create_op_asset(gazu_entity: dict) -> dict:
    """Create OP asset dict from gazu entity.

    :param gazu_entity:
    """
    return {
        "name": gazu_entity["name"],
        "type": "asset",
        "schema": "openpype:asset-3.0",
        "data": {"zou": gazu_entity, "tasks": {}},
    }


def set_op_project(dbcon, project_id) -> Collection:
    """Set project context.

    :param dbcon: Connection to DB.
    :param project_id: Project zou ID
    """
    import gazu

    project = gazu.project.get_project(project_id)
    project_name = project["name"]
    dbcon.Session["AVALON_PROJECT"] = project_name

    return dbcon.database[project_name]


def update_op_assets(
    entities_list: List[dict], asset_doc_ids: Dict[str, dict]
) -> List[Dict[str, dict]]:
    """Update OpenPype assets.
    Set 'data' and 'parent' fields.

    :param entities_list: List of zou entities to update
    :param asset_doc_ids: Dicts of [{zou_id: asset_doc}, ...]
    :return: List of (doc_id, update_dict) tuples
    """
    from gazu.task import (
        all_tasks_for_asset,
        all_tasks_for_shot,
    )

    assets_with_update = []
    for item in entities_list:
        # Update asset
        item_doc = asset_doc_ids[item["id"]]
        item_data = item_doc["data"].copy()
        item_data["zou"] = item

        # Tasks
        tasks_list = []
        if item["type"] == "Asset":
            tasks_list = all_tasks_for_asset(item)
        elif item["type"] == "Shot":
            tasks_list = all_tasks_for_shot(item)
            # TODO frame in and out
        item_data["tasks"] = {
            t["task_type_name"]: {"type": t["task_type_name"]}
            for t in tasks_list
        }

        # Get zou parent id for correct hierarchy
        # Use parent substitutes if existing
        substitute_parent_item = (
            item_data["parent_substitutes"][0]
            if item_data.get("parent_substitutes")
            else None
        )
        if substitute_parent_item:
            parent_zou_id = substitute_parent_item["parent_id"]
        else:
            parent_zou_id = (
                item.get("parent_id")
                or item.get("episode_id")
                or item.get("source_id")
            )  # TODO check consistency

        # Visual parent for hierarchy
        visual_parent_doc_id = (
            asset_doc_ids[parent_zou_id]["_id"] if parent_zou_id else None
        )
        item_data["visualParent"] = visual_parent_doc_id

        # Add parents for hierarchy
        item_data["parents"] = []
        while parent_zou_id is not None:
            parent_doc = asset_doc_ids[parent_zou_id]
            item_data["parents"].insert(0, parent_doc["name"])

            # Get parent entity
            parent_entity = parent_doc["data"]["zou"]
            parent_zou_id = parent_entity["parent_id"]

        # Update 'data' different in zou DB
        updated_data = {
            k: item_data[k]
            for k in item_data.keys()
            if item_doc["data"].get(k) != item_data[k]
        }
        if updated_data or not item_doc.get("parent"):
            assets_with_update.append(
                (
                    item_doc["_id"],
                    {
                        "$set": {
                            "name": item["name"],
                            "data": item_data,
                            "parent": asset_doc_ids[item["project_id"]]["_id"],
                        }
                    },
                )
            )

    return assets_with_update


def sync_project(project: dict, dbcon: AvalonMongoDB) -> UpdateOne:
    """Sync project with database.
    Create project if doesn't exist.

    :param project: Gazu project
    :param dbcon: DB to create project in
    :return: Update instance for the project
    """
    project_name = project["name"]
    project_doc = dbcon.find_one({"type": "project"})
    if not project_doc:
        print(f"Creating project '{project_name}'")
        project_doc = create_project(project_name, project_name, dbcon=dbcon)

    # Project data and tasks
    project_data = project["data"] or {}

    # Update data
    project_data.update(
        {
            "code": project["code"],
            "fps": project["fps"],
            "resolutionWidth": project["resolution"].split("x")[0],
            "resolutionHeight": project["resolution"].split("x")[1],
        }
    )

    return UpdateOne(
        {"_id": project_doc["_id"]},
        {
            "$set": {
                "config.tasks": {
                    t["name"]: {"short_name": t.get("short_name", t["name"])}
                    for t in gazu.task.all_task_types_for_project(project)
                },
                "data": project_data,
            }
        },
    )
