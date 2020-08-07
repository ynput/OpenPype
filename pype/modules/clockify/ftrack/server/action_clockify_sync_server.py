import os
import json
from pype.modules.ftrack.lib import BaseAction
from pype.modules.clockify.clockify_api import ClockifyAPI


class SyncClocifyServer(BaseAction):
    '''Synchronise project names and task types.'''

    identifier = "clockify.sync.server"
    label = "Sync To Clockify (server)"
    description = "Synchronise data to Clockify workspace"

    discover_role_list = ["Pypeclub", "Administrator", "project Manager"]

    def __init__(self, *args, **kwargs):
        super(SyncClocifyServer, self).__init__(*args, **kwargs)

        workspace_name = os.environ.get("CLOCKIFY_WORKSPACE")
        api_key = os.environ.get("CLOCKIFY_API_KEY")
        self.clockapi = ClockifyAPI(api_key)
        self.clockapi.set_workspace(workspace_name)
        if api_key is None:
            modified_key = "None"
        else:
            str_len = int(len(api_key) / 2)
            start_replace = int(len(api_key) / 4)
            modified_key = ""
            for idx in range(len(api_key)):
                if idx >= start_replace and idx < start_replace + str_len:
                    replacement = "X"
                else:
                    replacement = api_key[idx]
                modified_key += replacement

        self.log.info(
            "Clockify info. Workspace: \"{}\" API key: \"{}\"".format(
                str(workspace_name), str(modified_key)
            )
        )

    def discover(self, session, entities, event):
        if (
            len(entities) != 1
            or entities[0].entity_type.lower() != "project"
        ):
            return False

        # Get user and check his roles
        user_id = event.get("source", {}).get("user", {}).get("id")
        if not user_id:
            return False

        user = session.query("User where id is \"{}\"".format(user_id)).first()
        if not user:
            return False

        for role in user["user_security_roles"]:
            if role["security_role"]["name"] in self.discover_role_list:
                return True
        return False

    def register(self):
        self.session.event_hub.subscribe(
            "topic=ftrack.action.discover",
            self._discover,
            priority=self.priority
        )

        launch_subscription = (
            "topic=ftrack.action.launch and data.actionIdentifier={}"
        ).format(self.identifier)
        self.session.event_hub.subscribe(launch_subscription, self._launch)

    def launch(self, session, entities, event):
        if self.clockapi.workspace_id is None:
            return {
                "success": False,
                "message": "Clockify Workspace or API key are not set!"
            }

        if self.clockapi.validate_workspace_perm() is False:
            return {
                "success": False,
                "message": "Missing permissions for this action!"
            }

        # JOB SETTINGS
        user_id = event["source"]["user"]["id"]
        user = session.query("User where id is " + user_id).one()

        job = session.create("Job", {
            "user": user,
            "status": "running",
            "data": json.dumps({"description": "Sync Ftrack to Clockify"})
        })
        session.commit()

        project_entity = entities[0]
        if project_entity.entity_type.lower() != "project":
            project_entity = self.get_project_from_entity(project_entity)

        project_name = project_entity["full_name"]
        self.log.info(
            "Synchronization of project \"{}\" to clockify begins.".format(
                project_name
            )
        )
        task_types = (
            project_entity["project_schema"]["_task_type_schema"]["types"]
        )
        task_type_names = [
            task_type["name"] for task_type in task_types
        ]
        try:
            clockify_projects = self.clockapi.get_projects()
            if project_name not in clockify_projects:
                response = self.clockapi.add_project(project_name)
                if "id" not in response:
                    self.log.warning(
                        "Project \"{}\" can't be created. Response: {}".format(
                            project_name, response
                        )
                    )
                    return {
                        "success": False,
                        "message": (
                            "Can't create clockify project \"{}\"."
                            " Unexpected error."
                        ).format(project_name)
                    }

            clockify_workspace_tags = self.clockapi.get_tags()
            for task_type_name in task_type_names:
                if task_type_name in clockify_workspace_tags:
                    self.log.debug(
                        "Task \"{}\" already exist".format(task_type_name)
                    )
                    continue

                response = self.clockapi.add_tag(task_type_name)
                if "id" not in response:
                    self.log.warning(
                        "Task \"{}\" can't be created. Response: {}".format(
                            task_type_name, response
                        )
                    )

            job["status"] = "done"

        except Exception:
            self.log.warning(
                "Synchronization to clockify failed.",
                exc_info=True
            )

        finally:
            if job["status"] != "done":
                job["status"] = "failed"
            session.commit()

        return True


def register(session, **kw):
    SyncClocifyServer(session).register()
