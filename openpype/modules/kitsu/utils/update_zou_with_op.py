"""Functions to update Kitsu DB (a.k.a Zou) using OpenPype Data."""

import re
from typing import List

import gazu
from pymongo import UpdateOne

from openpype.pipeline import AvalonMongoDB
from openpype.api import get_project_settings
from openpype.modules.kitsu.utils.credentials import validate_credentials


def sync_zou(login: str, password: str):
    """Synchronize Zou database (Kitsu backend) with openpype database.
    This is an utility function to help updating zou data with OP's, it may not
    handle correctly all cases, a human intervention might
    be required after all.
    Will work better if OP DB has been previously synchronized from zou/kitsu.

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

    op_projects = [p for p in dbcon.projects()]
    for project_doc in op_projects:
        sync_zou_from_op_project(project_doc["name"], dbcon, project_doc)


def sync_zou_from_op_project(
    project_name: str, dbcon: AvalonMongoDB, project_doc: dict = None
) -> List[UpdateOne]:
    """Update OP project in DB with Zou data.

    Args:
        project_name (str): Name of project to sync
        dbcon (AvalonMongoDB): MongoDB connection
        project_doc (str, optional): Project doc to sync
    """
    # Get project doc if not provided
    if not project_doc:
        project_doc = dbcon.database[project_name].find_one(
            {"type": "project"}
        )

    # Get all entities from zou
    print(f"Synchronizing {project_name}...")
    zou_project = gazu.project.get_project_by_name(project_name)

    # Create project
    if zou_project is None:
        raise RuntimeError(
            f"Project '{project_name}' doesn't exist in Zou database, "
            "please create it in Kitsu and add OpenPype user to it before "
            "running synchronization."
        )

    # Update project settings and data
    if project_doc["data"]:
        zou_project.update(
            {
                "code": project_doc["data"]["code"],
                "fps": project_doc["data"]["fps"],
                "resolution": f"{project_doc['data']['resolutionWidth']}"
                f"x{project_doc['data']['resolutionHeight']}",
            }
        )
        gazu.project.update_project_data(zou_project, data=project_doc["data"])
    gazu.project.update_project(zou_project)

    asset_types = gazu.asset.all_asset_types()
    all_assets = gazu.asset.all_assets_for_project(zou_project)
    all_episodes = gazu.shot.all_episodes_for_project(zou_project)
    all_seqs = gazu.shot.all_sequences_for_project(zou_project)
    all_shots = gazu.shot.all_shots_for_project(zou_project)
    all_entities_ids = {
        e["id"] for e in all_episodes + all_seqs + all_shots + all_assets
    }

    # Query all assets of the local project
    project_module_settings = get_project_settings(project_name)["kitsu"]
    dbcon.Session["AVALON_PROJECT"] = project_name
    asset_docs = {
        asset_doc["_id"]: asset_doc
        for asset_doc in dbcon.find({"type": "asset"})
    }

    # Create new assets
    new_assets_docs = [
        doc
        for doc in asset_docs.values()
        if doc["data"].get("zou", {}).get("id") not in all_entities_ids
    ]
    naming_pattern = project_module_settings["entities_naming_pattern"]
    regex_ep = re.compile(
        r"(.*{}.*)|(.*{}.*)|(.*{}.*)".format(
            naming_pattern["shot"].replace("#", ""),
            naming_pattern["sequence"].replace("#", ""),
            naming_pattern["episode"].replace("#", ""),
        ),
        re.IGNORECASE,
    )
    bulk_writes = []
    for doc in new_assets_docs:
        visual_parent_id = doc["data"]["visualParent"]
        parent_substitutes = []

        # Match asset type by it's name
        match = regex_ep.match(doc["name"])
        if not match:  # Asset
            new_entity = gazu.asset.new_asset(
                zou_project, asset_types[0], doc["name"]
            )
        # Match case in shot<sequence<episode order to support
        # composed names like 'ep01_sq01_sh01'
        elif match.group(1):  # Shot
            # Match and check parent doc
            parent_doc = asset_docs[visual_parent_id]
            zou_parent_id = parent_doc["data"]["zou"]["id"]
            if parent_doc["data"].get("zou", {}).get("type") != "Sequence":
                # Substitute name
                digits_padding = naming_pattern["sequence"].count("#")
                episode_name = naming_pattern["episode"].replace(
                    "#" * digits_padding, "1".zfill(digits_padding)
                )
                sequence_name = naming_pattern["sequence"].replace(
                    "#" * digits_padding, "1".zfill(digits_padding)
                )
                substitute_sequence_name = f"{episode_name}_{sequence_name}"

                # Warn
                print(
                    f"Shot {doc['name']} must be parented to a Sequence "
                    "in Kitsu. "
                    f"Creating automatically one substitute sequence "
                    f"called {substitute_sequence_name} in Kitsu..."
                )

                # Create new sequence and set it as substitute
                created_sequence = gazu.shot.new_sequence(
                    zou_project,
                    substitute_sequence_name,
                    episode=zou_parent_id,
                )
                gazu.shot.update_sequence_data(
                    created_sequence, {"is_substitute": True}
                )
                parent_substitutes.append(created_sequence)

                # Update parent ID
                zou_parent_id = created_sequence["id"]

            # Create shot
            new_entity = gazu.shot.new_shot(
                zou_project,
                zou_parent_id,
                doc["name"],
                frame_in=doc["data"]["frameStart"],
                frame_out=doc["data"]["frameEnd"],
                nb_frames=doc["data"]["frameEnd"] - doc["data"]["frameStart"],
            )

        elif match.group(2):  # Sequence
            parent_doc = asset_docs[visual_parent_id]
            new_entity = gazu.shot.new_sequence(
                zou_project,
                doc["name"],
                episode=parent_doc["data"]["zou"]["id"],
            )

        elif match.group(3):  # Episode
            new_entity = gazu.shot.new_episode(zou_project, doc["name"])

        # Update doc with zou id
        doc["data"].update(
            {
                "visualParent": visual_parent_id,
                "zou": new_entity,
            }
        )
        bulk_writes.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "data.visualParent": visual_parent_id,
                        "data.zou": new_entity,
                        "data.parent_substitutes": parent_substitutes,
                    }
                },
            )
        )

    # Update assets
    all_tasks_types = {t["name"]: t for t in gazu.task.all_task_types()}
    assets_docs_to_update = [
        doc
        for doc in asset_docs.values()
        if doc["data"].get("zou", {}).get("id") in all_entities_ids
    ]
    for doc in assets_docs_to_update:
        zou_id = doc["data"]["zou"]["id"]
        if zou_id:
            # Data
            entity_data = {}
            frame_in = doc["data"].get("frameStart")
            frame_out = doc["data"].get("frameEnd")
            if frame_in or frame_out:
                entity_data.update(
                    {
                        "data": {
                            "frame_in": frame_in,
                            "frame_out": frame_out,
                        },
                        "nb_frames": frame_out - frame_in,
                    }
                )
            entity = gazu.raw.update("entities", zou_id, entity_data)

            # Tasks
            all_tasks_func = getattr(
                gazu.task, f"all_tasks_for_{entity['type'].lower()}"
            )
            entity_tasks = {t["name"] for t in all_tasks_func(entity)}
            for task_name in doc["data"]["tasks"].keys():
                # Create only if new
                if task_name not in entity_tasks:
                    task_type = all_tasks_types.get(task_name)

                    # Create non existing task
                    if not task_type:
                        task_type = gazu.task.new_task_type(task_name)
                        all_tasks_types[task_name] = task_type

                    # New task for entity
                    gazu.task.new_task(entity, task_type)

    # Delete
    deleted_entities = all_entities_ids - {
        asset_doc["data"].get("zou", {}).get("id")
        for asset_doc in asset_docs.values()
    }
    for entity_id in deleted_entities:
        gazu.raw.delete(f"data/entities/{entity_id}")

    # Write into DB
    if bulk_writes:
        dbcon.bulk_write(bulk_writes)
