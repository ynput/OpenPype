from pymongo import UpdateOne

from openpype_modules.ftrack.lib import BaseAction, statics_icon
from openpype.client import get_projects, get_project
from openpype.pipeline import AvalonMongoDB


class TestActionSyncProjectsStatus(BaseAction):
    """Action currently not used but meant to sync status of projects from ftrack to Avalon."""

    ignore_me = True  # Remove/comment this line to see the action in the ftrack menu

    identifier = 'test.action'
    label = 'Test action'
    description = 'Test action'

    icon = statics_icon("ftrack", "action_icons", "TestAction.svg")

    def __init__(self, session):
        self.dbcon = AvalonMongoDB()
        super().__init__(session)

    def discover(self, session, entities, event):
        return True

    def launch(self, session, entities, event):
        projects_to_be_deactived = []
        disabled_ftrack_projects = session.query(
            "select id from Project where status is_not active"
        ).all()

        disabled_ftrack_projects_id = [
            project['id'] for project in disabled_ftrack_projects
        ]
        mongo_projects = get_projects()

        for project in mongo_projects:
            if project['data'].get('ftrackId') in disabled_ftrack_projects_id:
                projects_to_be_deactived.append(project)
                self.log.debug(project['name'])

        # mongo_changes_bulk = []
        for project in projects_to_be_deactived:
            filter = {"_id": project["_id"]}
            change_data = {"$set": {'data.active': False}}
            self.dbcon.Session["AVALON_PROJECT"] = project['name']
            self.dbcon.bulk_write([UpdateOne(filter, change_data)])
            # mongo_changes_bulk.append(UpdateOne(filter, change_data))

        # if mongo_changes_bulk:
        #     self.dbcon.bulk_write(mongo_changes_bulk)

        return True


def register(session):
    TestActionSyncProjectsStatus(session).register()
