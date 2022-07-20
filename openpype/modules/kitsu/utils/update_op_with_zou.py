"""Functions to update OpenPype data using Kitsu DB (a.k.a Zou)."""
from copy import deepcopy
import re
from typing import Dict, List

from pymongo import DeleteOne, UpdateOne
import gazu
from gazu.task import (
    all_tasks_for_asset,
    all_tasks_for_shot,
)

from openpype.client import (
    get_project,
    get_assets,
    get_asset_by_id,
    get_asset_by_name,
)
from openpype.pipeline import AvalonMongoDB
from openpype.api import get_project_settings
from openpype.lib import create_project
from openpype.modules.kitsu.utils.credentials import validate_credentials


# Accepted namin pattern for OP
naming_pattern = re.compile("^[a-zA-Z0-9_.]*$")


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


def get_kitsu_project_name(project_id: str) -> str:
    """Get project name based on project id in kitsu.

    Args:
        project_id (str): UUID of project in Kitsu.

    Returns:
        str: Name of Kitsu project.
    """

    project = gazu.project.get_project(project_id)
    return project["name"]


def set_op_project(dbcon: AvalonMongoDB, project_id: str):
    """Set project context.

    Args:
        dbcon (AvalonMongoDB): Connection to DB
        project_id (str): Project zou ID
    """

    dbcon.Session["AVALON_PROJECT"] = get_kitsu_project_name(project_id)


def update_op_assets(
    dbcon: AvalonMongoDB,
    project_doc: dict,
    entities_list: List[dict],
    asset_doc_ids: Dict[str, dict],
) -> List[Dict[str, dict]]:
    """Update OpenPype assets.
    Set 'data' and 'parent' fields.

    Args:
        dbcon (AvalonMongoDB): Connection to DB
        entities_list (List[dict]): List of zou entities to update
        asset_doc_ids (Dict[str, dict]): Dicts of [{zou_id: asset_doc}, ...]

    Returns:
        List[Dict[str, dict]]: List of (doc_id, update_dict) tuples
    """
    project_name = project_doc["name"]
    project_module_settings = get_project_settings(project_name)["kitsu"]

    assets_with_update = []
    for item in entities_list:
        # Check asset exists
        item_doc = asset_doc_ids.get(item["id"])
        if not item_doc:  # Create asset
            op_asset = create_op_asset(item)
            insert_result = dbcon.insert_one(op_asset)
            item_doc = get_asset_by_id(project_name, insert_result.inserted_id)

        # Update asset
        item_data = deepcopy(item_doc["data"])
        item_data.update(item.get("data") or {})
        item_data["zou"] = item

        # == Asset settings ==
        # Frame in, fallback to project's value or default value (1001)
        # TODO: get default from settings/project_anatomy/attributes.json
        try:
            frame_in = int(
                item_data.pop(
                    "frame_in", project_doc["data"].get("frameStart")
                )
            )
        except (TypeError, ValueError):
            frame_in = 1001
        item_data["frameStart"] = frame_in
        # Frames duration, fallback on 0
        try:
            frames_duration = int(item_data.pop("nb_frames", 0))
        except (TypeError, ValueError):
            frames_duration = 0
        # Frame out, fallback on frame_in + duration or project's value or 1001
        frame_out = item_data.pop("frame_out", None)
        if not frame_out:
            frame_out = frame_in + frames_duration
        try:
            frame_out = int(frame_out)
        except (TypeError, ValueError):
            frame_out = 1001
        item_data["frameEnd"] = frame_out
        # Fps, fallback to project's value or default value (25.0)
        try:
            fps = float(item_data.get("fps", project_doc["data"].get("fps")))
        except (TypeError, ValueError):
            fps = 25.0
        item_data["fps"] = fps

        # Tasks
        tasks_list = []
        item_type = item["type"]
        if item_type == "Asset":
            tasks_list = all_tasks_for_asset(item)
        elif item_type == "Shot":
            tasks_list = all_tasks_for_shot(item)
        item_data["tasks"] = {
            t["task_type_name"]: {"type": t["task_type_name"], "zou": t}
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
                # For Asset, put under asset type directory
                item.get("entity_type_id")
                if item_type == "Asset"
                else None
                # Else, fallback on usual hierarchy
                or item.get("parent_id")
                or item.get("episode_id")
                or item.get("source_id")
            )

        # Substitute item type for general classification (assets or shots)
        if item_type in ["Asset", "AssetType"]:
            substitute_item_type = "assets"
        elif item_type in ["Episode", "Sequence"]:
            substitute_item_type = "shots"
        else:
            substitute_item_type = f"{item_type.lower()}s"
        entity_parent_folders = [
            f
            for f in project_module_settings["entities_root"]
            .get(substitute_item_type)
            .split("/")
            if f
        ]

        # Root parent folder if exist
        visual_parent_doc_id = (
            asset_doc_ids[parent_zou_id]["_id"] if parent_zou_id else None
        )
        if visual_parent_doc_id is None:
            # Find root folder docs
            root_folder_docs = get_assets(
                project_name,
                asset_names=[entity_parent_folders[-1]],
                fields=["_id", "data.root_of"],
            )
            # NOTE: Not sure why it's checking for entity type?
            #   OP3 does not support multiple assets with same names so type
            #       filtering is irelevant.
            # This way mimics previous implementation:
            # ```
            # root_folder_doc = dbcon.find_one(
            #     {
            #         "type": "asset",
            #         "name": entity_parent_folders[-1],
            #         "data.root_of": substitute_item_type,
            #     },
            #     ["_id"],
            # )
            # ```
            root_folder_doc = None
            for folder_doc in root_folder_docs:
                root_of = folder_doc.get("data", {}).get("root_of")
                if root_of == substitute_item_type:
                    root_folder_doc = folder_doc
                    break

            if root_folder_doc:
                visual_parent_doc_id = root_folder_doc["_id"]

        # Visual parent for hierarchy
        item_data["visualParent"] = visual_parent_doc_id

        # Add parents for hierarchy
        item_data["parents"] = []
        while parent_zou_id is not None:
            parent_doc = asset_doc_ids[parent_zou_id]
            item_data["parents"].insert(0, parent_doc["name"])

            # Get parent entity
            parent_entity = parent_doc["data"]["zou"]
            parent_zou_id = parent_entity.get("parent_id")

        # Set root folders parents
        item_data["parents"] = entity_parent_folders + item_data["parents"]

        # Update 'data' different in zou DB
        updated_data = {
            k: v for k, v in item_data.items() if item_doc["data"].get(k) != v
        }
        if updated_data or not item_doc.get("parent"):
            assets_with_update.append(
                (
                    item_doc["_id"],
                    {
                        "$set": {
                            "name": item["name"],
                            "data": item_data,
                            "parent": project_doc["_id"],
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
    project_doc = get_project(project_name)
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
            "fps": float(project["fps"]),
            "resolutionWidth": int(project["resolution"].split("x")[0]),
            "resolutionHeight": int(project["resolution"].split("x")[1]),
            "zou_id": project["id"],
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


def sync_all_projects(login: str, password: str):
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
    all_projects = gazu.project.all_open_projects()
    for project in all_projects:
        sync_project_from_kitsu(dbcon, project)


def sync_project_from_kitsu(dbcon: AvalonMongoDB, project: dict):
    """Update OP project in DB with Zou data.

    `root_of` is meant to sort entities by type for a better readability in the data tree. It
    puts all shot like (Shot and Episode and Sequence) and asset entities under two different root
    folders or hierarchy, defined in settings.

    Args:
        dbcon (AvalonMongoDB): MongoDB connection
        project (dict): Project dict got using gazu.
    """
    bulk_writes = []

    # Get project from zou
    if not project:
        project = gazu.project.get_project_by_name(project["name"])

    print(f"Synchronizing {project['name']}...")

    # Get all assets from zou
    all_assets = gazu.asset.all_assets_for_project(project)
    all_asset_types = gazu.asset.all_asset_types_for_project(project)
    all_episodes = gazu.shot.all_episodes_for_project(project)
    all_seqs = gazu.shot.all_sequences_for_project(project)
    all_shots = gazu.shot.all_shots_for_project(project)
    all_entities = [
        item
        for item in all_assets
        + all_asset_types
        + all_episodes
        + all_seqs
        + all_shots
        if naming_pattern.match(item["name"])
    ]

    # Sync project. Create if doesn't exist
    bulk_writes.append(write_project_to_op(project, dbcon))

    # Try to find project document
    project_name = project["name"]
    dbcon.Session["AVALON_PROJECT"] = project_name
    project_doc = get_project(project_name)

    # Query all assets of the local project
    zou_ids_and_asset_docs = {
        asset_doc["data"]["zou"]["id"]: asset_doc
        for asset_doc in get_assets(project_name)
        if asset_doc["data"].get("zou", {}).get("id")
    }
    zou_ids_and_asset_docs[project["id"]] = project_doc

    # Create entities root folders
    project_module_settings = get_project_settings(project_name)["kitsu"]
    for entity_type, root in project_module_settings["entities_root"].items():
        parent_folders = root.split("/")
        direct_parent_doc = None
        for i, folder in enumerate(parent_folders, 1):
            parent_doc = get_asset_by_name(
                project_name, folder, fields=["_id", "data.root_of"]
            )
            # NOTE: Not sure why it's checking for entity type?
            #   OP3 does not support multiple assets with same names so type
            #       filtering is irelevant.
            #   Also all of the entities could find be queried at once using
            #       'get_assets'.
            # This way mimics previous implementation:
            # ```
            # parent_doc = dbcon.find_one(
            #   {"type": "asset", "name": folder, "data.root_of": entity_type}
            # )
            # ```
            if (
                parent_doc
                and parent_doc.get("data", {}).get("root_of") != entity_type
            ):
                parent_doc = None

            if not parent_doc:
                direct_parent_doc = dbcon.insert_one(
                    {
                        "name": folder,
                        "type": "asset",
                        "schema": "openpype:asset-3.0",
                        "data": {
                            "root_of": entity_type,
                            "parents": parent_folders[:i],
                            "visualParent": direct_parent_doc.inserted_id
                            if direct_parent_doc
                            else None,
                            "tasks": {},
                        },
                    }
                )

    # Create
    to_insert = [
        create_op_asset(item)
        for item in all_entities
        if item["id"] not in zou_ids_and_asset_docs.keys()
    ]
    if to_insert:
        # Insert doc in DB
        dbcon.insert_many(to_insert)

        # Update existing docs
        zou_ids_and_asset_docs.update(
            {
                asset_doc["data"]["zou"]["id"]: asset_doc
                for asset_doc in get_assets(project_name)
                if asset_doc["data"].get("zou")
            }
        )

    # Update
    bulk_writes.extend(
        [
            UpdateOne({"_id": id}, update)
            for id, update in update_op_assets(
                dbcon, project_doc, all_entities, zou_ids_and_asset_docs
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
        dbcon.bulk_write(bulk_writes)
