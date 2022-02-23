from turtle import update
import gazu
import os

from pymongo import DeleteOne, UpdateOne

from avalon.api import AvalonMongoDB
from openpype.modules.default_modules.kitsu.utils.openpype import (
    create_op_asset,
    set_op_project,
    sync_project,
    update_op_assets,
)


def add_listeners():
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

    gazu.events.run_client(event_client)
