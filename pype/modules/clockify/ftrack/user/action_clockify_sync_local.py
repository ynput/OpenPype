import json
from pype.modules.ftrack.lib import BaseAction, statics_icon
from pype.modules.clockify.clockify_api import ClockifyAPI


class SyncClocifyLocal(BaseAction):
    '''Synchronise project names and task types.'''

    #: Action identifier.
    identifier = 'clockify.sync.local'
    #: Action label.
    label = 'Sync To Clockify (local)'
    #: Action description.
    description = 'Synchronise data to Clockify workspace'
    #: roles that are allowed to register this action
    role_list = ["Pypeclub", "Administrator", "project Manager"]
    #: icon
    icon = statics_icon("app_icons", "clockify-white.png")

    #: CLockifyApi
    clockapi = ClockifyAPI()

    def discover(self, session, entities, event):
        if (
            len(entities) == 1
            and entities[0].entity_type.lower() == "project"
        ):
            return True
        return False

    def launch(self, session, entities, event):
        self.clockapi.set_api()
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
        userId = event['source']['user']['id']
        user = session.query('User where id is ' + userId).one()

        job = session.create('Job', {
            'user': user,
            'status': 'running',
            'data': json.dumps({
                'description': 'Sync Ftrack to Clockify'
            })
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
            pass

        finally:
            if job["status"] != "done":
                job["status"] = "failed"
            session.commit()

        return True


def register(session, **kw):
    SyncClocifyLocal(session).register()
