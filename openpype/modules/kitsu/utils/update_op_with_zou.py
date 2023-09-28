"""Functions to update OpenPype data using Kitsu DB (a.k.a Zou)."""
from copy import deepcopy
import re
from typing import Dict, List

from pymongo import DeleteOne, UpdateOne
import gazu

from openpype.client import (
    get_project,
    get_assets,
    get_asset_by_id,
    get_asset_by_name,
    create_project,
)
from openpype.pipeline import AvalonMongoDB
from openpype.modules.kitsu.utils.credentials import validate_credentials

from openpype.lib import Logger

log = Logger.get_logger(__name__)

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
    gazu_project: dict,
    project_doc: dict,
    entities_list: List[dict],
    asset_doc_ids: Dict[str, dict],
) -> List[Dict[str, dict]]:
    """Update OpenPype assets.
    Set 'data' and 'parent' fields.

    Args:
        dbcon (AvalonMongoDB): Connection to DB
        gazu_project (dict): Dict of gazu,
        project_doc (dict): Dict of project,
        entities_list (List[dict]): List of zou entities to update
        asset_doc_ids (Dict[str, dict]): Dicts of [{zou_id: asset_doc}, ...]

    Returns:
        List[Dict[str, dict]]: List of (doc_id, update_dict) tuples
    """
    if not project_doc:
        return

    project_name = project_doc["name"]

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
        # Frames duration, fallback on 1
        try:
            # NOTE nb_frames is stored directly in item
            # because of zou's legacy design
            frames_duration = int(item.get("nb_frames", 1))
        except (TypeError, ValueError):
            frames_duration = None
        # Frame out, fallback on frame_in + duration or project's value or 1001
        frame_out = item_data.pop("frame_out", None)
        if not frame_out:
            if frames_duration:
                frame_out = frame_in + frames_duration - 1
            else:
                frame_out = project_doc["data"].get("frameEnd", frame_in)
        item_data["frameEnd"] = int(frame_out)
        # Fps, fallback to project's value or default value (25.0)
        try:
            fps = float(item_data.get("fps"))
        except (TypeError, ValueError):
            fps = float(
                gazu_project.get("fps", project_doc["data"].get("fps", 25))
            )
        item_data["fps"] = fps
        # Resolution, fall back to project default
        match_res = re.match(
            r"(\d+)x(\d+)",
            item_data.get("resolution", gazu_project.get("resolution")),
        )
        if match_res:
            item_data["resolutionWidth"] = int(match_res.group(1))
            item_data["resolutionHeight"] = int(match_res.group(2))
        else:
            item_data["resolutionWidth"] = int(
                project_doc["data"].get("resolutionWidth")
            )
            item_data["resolutionHeight"] = int(
                project_doc["data"].get("resolutionHeight")
            )
        # Properties that doesn't fully exist in Kitsu.
        # Guessing those property names below:
        # Pixel Aspect Ratio
        item_data["pixelAspect"] = float(
            item_data.get(
                "pixel_aspect", project_doc["data"].get("pixelAspect")
            )
        )
        # Handle Start
        item_data["handleStart"] = int(
            item_data.get(
                "handle_start", project_doc["data"].get("handleStart")
            )
        )
        # Handle End
        item_data["handleEnd"] = int(
            item_data.get("handle_end", project_doc["data"].get("handleEnd"))
        )
        # Clip In
        item_data["clipIn"] = int(
            item_data.get("clip_in", project_doc["data"].get("clipIn"))
        )
        # Clip Out
        item_data["clipOut"] = int(
            item_data.get("clip_out", project_doc["data"].get("clipOut"))
        )

        # Tasks
        tasks_list = []
        item_type = item["type"]
        if item_type == "Asset":
            tasks_list = gazu.task.all_tasks_for_asset(item)
        elif item_type == "Shot":
            tasks_list = gazu.task.all_tasks_for_shot(item)
        elif item_type == "Sequence":
            tasks_list = gazu.task.all_tasks_for_sequence(item)
        item_data["tasks"] = {
            t["task_type_name"]: {
                "type": t["task_type_name"],
                "zou": gazu.task.get_task(t["id"]),
            }
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
            entity_root_asset_name = "Assets"
        elif item_type in ["Episode", "Sequence", "Shot"]:
            entity_root_asset_name = "Shots"

        # Root parent folder if exist
        visual_parent_doc_id = None
        if parent_zou_id is not None:
            parent_zou_id_dict = asset_doc_ids.get(parent_zou_id)
            if parent_zou_id_dict is not None:
                visual_parent_doc_id = (
                    parent_zou_id_dict.get("_id")
                    if parent_zou_id_dict
                    else None
                )

        if visual_parent_doc_id is None:
            # Find root folder doc ("Assets" or "Shots")
            root_folder_doc = get_asset_by_name(
                project_name,
                asset_name=entity_root_asset_name,
                fields=["_id", "data.root_of"],
            )

            if root_folder_doc:
                visual_parent_doc_id = root_folder_doc["_id"]

        # Visual parent for hierarchy
        item_data["visualParent"] = visual_parent_doc_id

        # Add parents for hierarchy
        item_data["parents"] = []
        ancestor_id = parent_zou_id
        while ancestor_id is not None:
            parent_doc = asset_doc_ids.get(ancestor_id)
            if parent_doc is not None:
                item_data["parents"].insert(0, parent_doc["name"])

                # Get parent entity
                parent_entity = parent_doc["data"]["zou"]
                ancestor_id = parent_entity.get("parent_id")
            else:
                ancestor_id = None

        # # Build OpenPype compatible name   DISABLED AND REPLACED BY BLOCK BELOW
        # if item_type in ["Shot", "Sequence"] and parent_zou_id is not None:
        #     # Name with parents hierarchy "({episode}_){sequence}_{shot}"
        #     # to avoid duplicate name issue
        #     item_name = f"{item_data['parents'][-1]}_{item['name']}"

        #     # Update doc name
        #     asset_doc_ids[item["id"]]["name"] = item_name
        # else:
        #     item_name = item["name"]

        # PASS NAME UNCHANGED:
        item_name = item["name"]

        # Set root folders parents
        item_data["parents"] = [entity_root_asset_name] + item_data["parents"]

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
                            "name": item_name,
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
    project_dict = get_project(project_name)
    if not project_dict:
        project_dict = create_project(project_name, project_name)

    # Project data and tasks
    project_data = project_dict["data"] or {}

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
            "zou_id": project["id"],
            "active": project["project_status_name"] != "Closed",
        }
    )

    match_res = re.match(r"(\d+)x(\d+)", project["resolution"])
    if match_res:
        project_data["resolutionWidth"] = int(match_res.group(1))
        project_data["resolutionHeight"] = int(match_res.group(2))
    else:
        log.warning(
            f"'{project['resolution']}' does not match the expected"
            " format for the resolution, for example: 1920x1080"
        )

    return UpdateOne(
        {"_id": project_dict["_id"]},
        {
            "$set": {
                "config.tasks": {
                    t["name"]: {"short_name": t.get("short_name", t["name"])}
                    for t in gazu.task.all_task_types_for_project(project)
                    or gazu.task.all_task_types()
                },
                "data": project_data,
            }
        },
    )


def sync_all_projects(
    login: str,
    password: str,
    ignore_projects: list = None,
    filter_projects: tuple = None,
):
    """Update all OP projects in DB with Zou data.

    Args:
        login (str): Kitsu user login
        password (str): Kitsu user password
        ignore_projects (list): List of unsynced project names
        filter_projects (tuple): Tuple of filter project names to sync with
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

    project_to_sync = []

    if filter_projects:
        all_kitsu_projects = {p["name"]: p for p in all_projects}
        for proj_name in filter_projects:
            if proj_name in all_kitsu_projects:
                project_to_sync.append(all_kitsu_projects[proj_name])
            else:
                log.info(
                    f"`{proj_name}` project does not exist in Kitsu."
                    f" Please make sure the project is spelled correctly."
                )
    else:
        # all project
        project_to_sync = all_projects

    for project in project_to_sync:
        if ignore_projects and project["name"] in ignore_projects:
            continue
        sync_project_from_kitsu(dbcon, project)


def sync_project_from_kitsu(dbcon: AvalonMongoDB, project: dict):
    """Update OP project in DB with Zou data.

    `root_of` is meant to sort entities by type for a better readability in
    the data tree. It puts all shot like (Shot and Episode and Sequence) and
    asset entities under two different root folders or hierarchy, defined in
    settings.

    Args:
        dbcon (AvalonMongoDB): MongoDB connection
        project (dict): Project dict got using gazu.
    """
    bulk_writes = []

    # Get project from zou
    if not project:
        project = gazu.project.get_project_by_name(project["name"])

    # Get all statuses for projects from Kitsu
    all_status = gazu.project.all_project_status()
    for status in all_status:
        if project["project_status_id"] == status["id"]:
            project["project_status_name"] = status["name"]
            break

    #  Do not sync closed kitsu project that is not found in openpype
    if project["project_status_name"] == "Closed" and not get_project(
        project["name"]
    ):
        return

    log.info(f"Synchronizing {project['name']}...")

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
    project_name = project["name"]
    project_dict = get_project(project_name)
    if not project_dict:
        log.info("Project created: {}".format(project_name))
    bulk_writes.append(write_project_to_op(project, dbcon))

    if project["project_status_name"] == "Closed":
        return

    # Try to find project document
    if not project_dict:
        project_dict = get_project(project_name)
    dbcon.Session["AVALON_PROJECT"] = project_name

    # Query all assets of the local project
    zou_ids_and_asset_docs = {
        asset_doc["data"]["zou"]["id"]: asset_doc
        for asset_doc in get_assets(project_name)
        if asset_doc["data"].get("zou", {}).get("id")
    }
    zou_ids_and_asset_docs[project["id"]] = project_dict

    # Create entities root folders
    to_insert = [
        {
            "name": r,
            "type": "asset",
            "schema": "openpype:asset-3.0",
            "data": {
                "root_of": r,
                "tasks": {},
                "visualParent": None,
                "parents": [],
            },
        }
        for r in ["Assets", "Shots"]
        if not get_asset_by_name(
            project_name, r, fields=["_id", "data.root_of"]
        )
    ]

    # Create
    to_insert.extend(
        [
            create_op_asset(item)
            for item in all_entities
            if item["id"] not in zou_ids_and_asset_docs.keys()
        ]
    )
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
                dbcon,
                project,
                project_dict,
                all_entities,
                zou_ids_and_asset_docs,
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
