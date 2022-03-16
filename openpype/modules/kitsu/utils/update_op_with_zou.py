"""Functions to update OpenPype data using Kitsu DB (a.k.a Zou)."""
from typing import Dict, List

from pymongo import DeleteOne, UpdateOne
from pymongo.collection import Collection
import gazu
from gazu.task import (
    all_tasks_for_asset,
    all_tasks_for_shot,
)

from avalon.api import AvalonMongoDB
from openpype.lib import create_project
from openpype.modules.kitsu.utils.credentials import validate_credentials


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


def write_project_to_op(project: dict, dbcon: AvalonMongoDB) -> UpdateOne:
    """Write gazu project to OP database.
    Create project if doesn't exist.

    Args:
        project (dict): Gazu project
        dbcon (AvalonMongoDB): DB to create project in

    Returns:
        UpdateOne: Update instance for the project
    """
    project_name = project["name"]
    project_doc = dbcon.database[project_name].find_one({"type": "project"})
    if not project_doc:
        print(f"Creating project '{project_name}'")
        project_doc = create_project(project_name, project_name, dbcon=dbcon)

    # Project data and tasks
    project_data = project["data"] or {}

    # Build project code and update Kitsu
    project_code = project.get("code")
    if not project_code:
        project_code = project["name"].replace(" ", "_").lower()
        project["code"] = project_code

        # Update Zou
        gazu.project.update_project(project)

    # Update data
    project_data.update(
        {
            "code": project_code,
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


def sync_all_project(login: str, password: str):
    """Update all OP projects in DB with Zou data.

    Args:
        login (str): Kitsu user login
        password (str): Kitsu user password

    Raises:
        gazu.exception.AuthFailedException: Wrong user login and/or password
    """

    # Authenticate
    if not validate_credentials(login, password):
        raise gazu.exception.AuthFailedException(
            f"Kitsu authentication failed for login: '{login}'..."
        )

    # Iterate projects
    dbcon = AvalonMongoDB()
    dbcon.install()
    all_projects = gazu.project.all_projects()
    for project in all_projects:
        sync_project_from_kitsu(project["name"], dbcon, project)


def sync_project_from_kitsu(
    project_name: str, dbcon: AvalonMongoDB, project: dict = None
):
    """Update OP project in DB with Zou data.

    Args:
        project_name (str): Name of project to sync
        dbcon (AvalonMongoDB): MongoDB connection
        project (dict, optional): Project dict got using gazu.
                                  Defaults to None.
    """
    bulk_writes = []

    # Get project from zou
    if not project:
        project = gazu.project.get_project_by_name(project_name)
    project_code = project_name

    print(f"Synchronizing {project_name}...")

    # Get all assets from zou
    all_assets = gazu.asset.all_assets_for_project(project)
    all_episodes = gazu.shot.all_episodes_for_project(project)
    all_seqs = gazu.shot.all_sequences_for_project(project)
    all_shots = gazu.shot.all_shots_for_project(project)
    all_entities = all_assets + all_episodes + all_seqs + all_shots

    # Sync project. Create if doesn't exist
    bulk_writes.append(write_project_to_op(project, dbcon))

    # Try to find project document
    project_col = dbcon.database[project_code]
    project_doc = project_col.find_one({"type": "project"})

    # Query all assets of the local project
    zou_ids_and_asset_docs = {
        asset_doc["data"]["zou"]["id"]: asset_doc
        for asset_doc in project_col.find({"type": "asset"})
        if asset_doc["data"].get("zou", {}).get("id")
    }
    zou_ids_and_asset_docs[project["id"]] = project_doc

    # Create
    to_insert = []
    to_insert.extend(
        [
            create_op_asset(item)
            for item in all_entities
            if item["id"] not in zou_ids_and_asset_docs.keys()
        ]
    )
    if to_insert:
        # Insert doc in DB
        project_col.insert_many(to_insert)

        # Update existing docs
        zou_ids_and_asset_docs.update(
            {
                asset_doc["data"]["zou"]["id"]: asset_doc
                for asset_doc in project_col.find({"type": "asset"})
                if asset_doc["data"].get("zou")
            }
        )

    # Update
    bulk_writes.extend(
        [
            UpdateOne({"_id": id}, update)
            for id, update in update_op_assets(
                all_entities, zou_ids_and_asset_docs
            )
        ]
    )

    # Delete
    diff_assets = set(zou_ids_and_asset_docs.keys()) - {
        e["id"] for e in all_entities + [project]
    }
    if diff_assets:
        bulk_writes.extend(
            [
                DeleteOne(zou_ids_and_asset_docs[asset_id])
                for asset_id in diff_assets
            ]
        )

    # Write into DB
    if bulk_writes:
        project_col.bulk_write(bulk_writes)
