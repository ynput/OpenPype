from openpype.client import get_projects, get_project
from openpype_modules.clockify.clockify_api import ClockifyAPI
from openpype.pipeline import LauncherAction
from openpype.lib.local_settings import OpenPypeSecureRegistry



class ClockifySync(LauncherAction):

    name = "sync_to_clockify"
    label = "Sync to Clockify"
    icon = "app_icons/clockify-white.png"
    order = 500
    reg = OpenPypeSecureRegistry("clockify")
    api_key = reg.get_item("api_key")
    clockapi = ClockifyAPI(api_key=api_key)
    clockapi.verify_api()
    have_permissions = clockapi.validate_workspace_perm() or True

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        return self.have_permissions

    def process(self, session, **kwargs):
        project_name = session.get("AVALON_PROJECT") or ""

        user_id = self.clockapi.get_user_id()
        workspace_id = self.clockapi.get_workspace_id("test_workspace")

        projects_to_sync = []
        if project_name.strip():
            projects_to_sync = [get_project(project_name)]
        else:
            projects_to_sync = get_projects()

        projects_info = {}
        for project in projects_to_sync:
            task_types = project["config"]["tasks"].keys()
            projects_info[project["name"]] = task_types

        clockify_projects = self.clockapi.get_projects(workspace_id)
        for project_name, task_types in projects_info.items():
            if project_name in clockify_projects:
                continue

            response = self.clockapi.add_project(project_name, workspace_id)
            if "id" not in response:
                self.log.error("Project {} can't be created".format(
                    project_name
                ))
                continue

            clockify_workspace_tags = self.clockapi.get_tags(workspace_id)
            for task_type in task_types:
                if task_type not in clockify_workspace_tags:
                    response = self.clockapi.add_tag(task_type, workspace_id)
                    if "id" not in response:
                        self.log.error('Task {} can\'t be created'.format(
                            task_type
                        ))
                        continue
