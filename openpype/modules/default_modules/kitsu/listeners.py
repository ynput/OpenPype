from turtle import update
import gazu
import os

from pymongo import DeleteOne, UpdateOne

from avalon.api import AvalonMongoDB
from openpype.modules.default_modules.kitsu.utils.openpype import sync_project


def add_listeners():
    # Connect to server
    gazu.client.set_host(os.environ["KITSU_SERVER"])

    # Authenticate
    gazu.log_in(os.environ["KITSU_LOGIN"], os.environ["KITSU_PWD"])
    gazu.set_event_host(os.environ["KITSU_SERVER"].replace("api", "socket.io"))

    # Connect to DB
    dbcon = AvalonMongoDB()
    dbcon.install()

    def new_project(data):
        """Create new project into DB."""

        # Use update process to avoid duplicating code
        update_project(data)

    def update_project(data):
        """Update project into DB."""
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
        # Get project entity
        print(data)  # TODO check bugfix
        project = gazu.project.get_project(data["project_id"])

        # Delete project collection
        project_col = dbcon.database[project["name"]]
        project_col.drop()

    def new_asset(data):
        print("Asset created %s" % data)

    event_client = gazu.events.init()
    gazu.events.add_listener(event_client, "project:new", new_project)
    gazu.events.add_listener(event_client, "project:update", update_project)
    gazu.events.add_listener(event_client, "project:delete", delete_project)
    gazu.events.add_listener(event_client, "asset:new", new_asset)
    gazu.events.run_client(event_client)
    print("ll")
