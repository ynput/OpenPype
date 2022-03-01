import gazu
import os

from avalon.api import AvalonMongoDB
from .openpype import (
    create_op_asset,
    set_op_project,
    sync_project,
    update_op_assets,
)


def start_listeners():
    """Start listeners to keep OpenPype up-to-date with Kitsu."""
    # Connect to server
    gazu.client.set_host(os.environ["KITSU_SERVER"])

    # Authenticate
    gazu.log_in(os.environ["KITSU_LOGIN"], os.environ["KITSU_PWD"])
    gazu.set_event_host(os.environ["KITSU_SERVER"].replace("api", "socket.io"))
    event_client = gazu.events.init()

    # Connect to DB
    dbcon = AvalonMongoDB()
    dbcon.install()

    # == Project ==

    def new_project(data):
        """Create new project into OP DB."""

        # Use update process to avoid duplicating code
        update_project(data)

    def update_project(data):
        """Update project into OP DB."""
        # Get project entity
        project = gazu.project.get_project(data["project_id"])
        project_name = project["name"]
        dbcon.Session["AVALON_PROJECT"] = project_name

        update_project = sync_project(project, dbcon)

        # Write into DB
        if update_project:
            project_col = dbcon.database[project_name]
            project_col.bulk_write([update_project])

    def delete_project(data):
        """Delete project."""
        # Get project entity
        print(data)  # TODO check bugfix
        project = gazu.project.get_project(data["project_id"])

        # Delete project collection
        project_col = dbcon.database[project["name"]]
        project_col.drop()

    gazu.events.add_listener(event_client, "project:new", new_project)
    gazu.events.add_listener(event_client, "project:update", update_project)
    gazu.events.add_listener(event_client, "project:delete", delete_project)

    # == Asset ==

    def new_asset(data):
        """Create new asset into OP DB."""
        # Get project entity
        project_col = set_op_project(dbcon, data["project_id"])

        # Get gazu entity
        asset = gazu.asset.get_asset(data["asset_id"])

        # Insert doc in DB
        project_col.insert_one(create_op_asset(asset))

        # Update
        update_asset(data)

    def update_asset(data):
        """Update asset into OP DB."""
        project_col = set_op_project(dbcon, data["project_id"])
        project_doc = dbcon.find_one({"type": "project"})

        # Get gazu entity
        asset = gazu.asset.get_asset(data["asset_id"])

        # Find asset doc
        # Query all assets of the local project
        zou_ids_and_asset_docs = {
            asset_doc["data"]["zou"]["id"]: asset_doc
            for asset_doc in project_col.find({"type": "asset"})
            if asset_doc["data"].get("zou", {}).get("id")
        }
        zou_ids_and_asset_docs[asset["project_id"]] = project_doc

        # Update
        asset_doc_id, asset_update = update_op_assets([asset], zou_ids_and_asset_docs)[
            0
        ]
        project_col.update_one({"_id": asset_doc_id}, asset_update)

    def delete_asset(data):
        """Delete asset of OP DB."""
        project_col = set_op_project(dbcon, data["project_id"])

        # Delete
        project_col.delete_one({"type": "asset", "data.zou.id": data["asset_id"]})

    gazu.events.add_listener(event_client, "asset:new", new_asset)
    gazu.events.add_listener(event_client, "asset:update", update_asset)
    gazu.events.add_listener(event_client, "asset:delete", delete_asset)

    # == Episode ==
    def new_episode(data):
        """Create new episode into OP DB."""
        # Get project entity
        project_col = set_op_project(dbcon, data["project_id"])

        # Get gazu entity
        episode = gazu.shot.get_episode(data["episode_id"])

        # Insert doc in DB
        project_col.insert_one(create_op_asset(episode))

        # Update
        update_episode(data)

    def update_episode(data):
        """Update episode into OP DB."""
        project_col = set_op_project(dbcon, data["project_id"])
        project_doc = dbcon.find_one({"type": "project"})

        # Get gazu entity
        episode = gazu.shot.get_episode(data["episode_id"])

        # Find asset doc
        # Query all assets of the local project
        zou_ids_and_asset_docs = {
            asset_doc["data"]["zou"]["id"]: asset_doc
            for asset_doc in project_col.find({"type": "asset"})
            if asset_doc["data"].get("zou", {}).get("id")
        }
        zou_ids_and_asset_docs[episode["project_id"]] = project_doc

        # Update
        asset_doc_id, asset_update = update_op_assets(
            [episode], zou_ids_and_asset_docs
        )[0]
        project_col.update_one({"_id": asset_doc_id}, asset_update)

    def delete_episode(data):
        """Delete shot of OP DB."""
        project_col = set_op_project(dbcon, data["project_id"])
        print("delete episode")  # TODO check bugfix

        # Delete
        project_col.delete_one({"type": "asset", "data.zou.id": data["episode_id"]})

    gazu.events.add_listener(event_client, "episode:new", new_episode)
    gazu.events.add_listener(event_client, "episode:update", update_episode)
    gazu.events.add_listener(event_client, "episode:delete", delete_episode)

    # == Sequence ==
    def new_sequence(data):
        """Create new sequnce into OP DB."""
        # Get project entity
        project_col = set_op_project(dbcon, data["project_id"])

        # Get gazu entity
        sequence = gazu.shot.get_sequence(data["sequence_id"])

        # Insert doc in DB
        project_col.insert_one(create_op_asset(sequence))

        # Update
        update_sequence(data)

    def update_sequence(data):
        """Update sequence into OP DB."""
        project_col = set_op_project(dbcon, data["project_id"])
        project_doc = dbcon.find_one({"type": "project"})

        # Get gazu entity
        sequence = gazu.shot.get_sequence(data["sequence_id"])

        # Find asset doc
        # Query all assets of the local project
        zou_ids_and_asset_docs = {
            asset_doc["data"]["zou"]["id"]: asset_doc
            for asset_doc in project_col.find({"type": "asset"})
            if asset_doc["data"].get("zou", {}).get("id")
        }
        zou_ids_and_asset_docs[sequence["project_id"]] = project_doc

        # Update
        asset_doc_id, asset_update = update_op_assets(
            [sequence], zou_ids_and_asset_docs
        )[0]
        project_col.update_one({"_id": asset_doc_id}, asset_update)

    def delete_sequence(data):
        """Delete sequence of OP DB."""
        project_col = set_op_project(dbcon, data["project_id"])
        print("delete sequence")  # TODO check bugfix

        # Delete
        project_col.delete_one({"type": "asset", "data.zou.id": data["sequence_id"]})

    gazu.events.add_listener(event_client, "sequence:new", new_sequence)
    gazu.events.add_listener(event_client, "sequence:update", update_sequence)
    gazu.events.add_listener(event_client, "sequence:delete", delete_sequence)

    # == Shot ==
    def new_shot(data):
        """Create new shot into OP DB."""
        # Get project entity
        project_col = set_op_project(dbcon, data["project_id"])

        # Get gazu entity
        shot = gazu.shot.get_shot(data["shot_id"])

        # Insert doc in DB
        project_col.insert_one(create_op_asset(shot))

        # Update
        update_shot(data)

    def update_shot(data):
        """Update shot into OP DB."""
        project_col = set_op_project(dbcon, data["project_id"])
        project_doc = dbcon.find_one({"type": "project"})

        # Get gazu entity
        shot = gazu.shot.get_shot(data["shot_id"])

        # Find asset doc
        # Query all assets of the local project
        zou_ids_and_asset_docs = {
            asset_doc["data"]["zou"]["id"]: asset_doc
            for asset_doc in project_col.find({"type": "asset"})
            if asset_doc["data"].get("zou", {}).get("id")
        }
        zou_ids_and_asset_docs[shot["project_id"]] = project_doc

        # Update
        asset_doc_id, asset_update = update_op_assets([shot], zou_ids_and_asset_docs)[0]
        project_col.update_one({"_id": asset_doc_id}, asset_update)

    def delete_shot(data):
        """Delete shot of OP DB."""
        project_col = set_op_project(dbcon, data["project_id"])

        # Delete
        project_col.delete_one({"type": "asset", "data.zou.id": data["shot_id"]})

    gazu.events.add_listener(event_client, "shot:new", new_shot)
    gazu.events.add_listener(event_client, "shot:update", update_shot)
    gazu.events.add_listener(event_client, "shot:delete", delete_shot)

    # == Task ==
    def new_task(data):
        """Create new task into OP DB."""
        print("new", data)
        # Get project entity
        project_col = set_op_project(dbcon, data["project_id"])

        # Get gazu entity
        task = gazu.task.get_task(data["task_id"])

        # Find asset doc
        asset_doc = project_col.find_one(
            {"type": "asset", "data.zou.id": task["entity"]["id"]}
        )

        # Update asset tasks with new one
        asset_tasks = asset_doc["data"].get("tasks")
        task_type_name = task["task_type"]["name"]
        asset_tasks[task_type_name] = {"type": task_type_name, "zou": task}
        project_col.update_one(
            {"_id": asset_doc["_id"]}, {"$set": {"data.tasks": asset_tasks}}
        )

    def update_task(data):
        """Update task into OP DB."""
        # TODO is it necessary?
        pass

    def delete_task(data):
        """Delete task of OP DB."""
        project_col = set_op_project(dbcon, data["project_id"])

        # Find asset doc
        asset_docs = [doc for doc in project_col.find({"type": "asset"})]
        for doc in asset_docs:
            # Match task
            for name, task in doc["data"]["tasks"].items():
                if task.get("zou") and data["task_id"] == task["zou"]["id"]:
                    # Pop task
                    asset_tasks = doc["data"].get("tasks")
                    asset_tasks.pop(name)

                    # Delete task in DB
                    project_col.update_one(
                        {"_id": doc["_id"]}, {"$set": {"data.tasks": asset_tasks}}
                    )
                    return

    gazu.events.add_listener(event_client, "task:new", new_task)
    gazu.events.add_listener(event_client, "task:update", update_task)
    gazu.events.add_listener(event_client, "task:delete", delete_task)

    gazu.events.run_client(event_client)
