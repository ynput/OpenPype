import os
import re
import time
import json
import datetime
import requests
from .constants import (
    CLOCKIFY_ENDPOINT,
    ADMIN_PERMISSION_NAMES
)

from openpype.lib.local_settings import OpenPypeSecureRegistry


def time_check(obj):
    if obj.request_counter < 10:
        obj.request_counter += 1
        return

    wait_time = 1 - (time.time() - obj.request_time)
    if wait_time > 0:
        time.sleep(wait_time)

    obj.request_time = time.time()
    obj.request_counter = 0


class ClockifyAPI:
    def __init__(self, api_key=None, master_parent=None):
        self.workspace_name = None
        self.workspace_id = None
        self.master_parent = master_parent
        self.api_key = api_key
        self.request_counter = 0
        self.request_time = time.time()

        self._secure_registry = None

    @property
    def secure_registry(self):
        if self._secure_registry is None:
            self._secure_registry = OpenPypeSecureRegistry("clockify")
        return self._secure_registry

    @property
    def headers(self):
        return {"X-Api-Key": self.api_key}

    def verify_api(self):
        for key, value in self.headers.items():
            if value is None or value.strip() == '':
                return False
        return True

    def set_api(self, api_key=None):
        if api_key is None:
            api_key = self.get_api_key()

        if api_key is not None and self.validate_api_key(api_key) is True:
            self.api_key = api_key
            self.set_workspace()
            if self.master_parent:
                self.master_parent.signed_in()
            return True
        return False

    def validate_api_key(self, api_key):
        test_headers = {'X-Api-Key': api_key}
        action_url = 'workspaces/'
        time_check(self)
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=test_headers
        )
        if response.status_code != 200:
            return False
        return True

    def validate_workspace_perm(self, workspace_id=None):
        user_id = self.get_user_id()
        if user_id is None:
            return False
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = "/workspaces/{}/users/{}/permissions".format(
            workspace_id, user_id
        )
        time_check(self)
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )
        user_permissions = response.json()
        for perm in user_permissions:
            if perm['name'] in ADMIN_PERMISSION_NAMES:
                return True
        return False

    def get_user_id(self):
        action_url = 'v1/user/'
        time_check(self)
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )
        # this regex is neccessary: UNICODE strings are crashing
        # during json serialization
        id_regex = '\"{1}id\"{1}\:{1}\"{1}\w+\"{1}'
        result = re.findall(id_regex, str(response.content))
        if len(result) != 1:
            # replace with log and better message?
            print('User ID was not found (this is a BUG!!!)')
            return None
        return json.loads('{'+result[0]+'}')['id']

    def set_workspace(self, name=None):
        if name is None:
            name = os.environ.get('CLOCKIFY_WORKSPACE', None)
        self.workspace_name = name
        self.workspace_id = None
        if self.workspace_name is None:
            return
        try:
            result = self.validate_workspace()
        except Exception:
            result = False
        if result is not False:
            self.workspace_id = result
            if self.master_parent is not None:
                self.master_parent.start_timer_check()
            return True
        return False

    def validate_workspace(self, name=None):
        if name is None:
            name = self.workspace_name
        all_workspaces = self.get_workspaces()
        if name in all_workspaces:
            return all_workspaces[name]
        return False

    def get_api_key(self):
        return self.secure_registry.get_item("api_key", None)

    def save_api_key(self, api_key):
        self.secure_registry.set_item("api_key", api_key)

    def get_workspaces(self):
        action_url = 'workspaces/'
        time_check(self)
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )
        return {
            workspace["name"]: workspace["id"] for workspace in response.json()
        }

    def get_projects(self, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = 'workspaces/{}/projects/'.format(workspace_id)
        time_check(self)
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )

        return {
            project["name"]: project["id"] for project in response.json()
        }

    def get_project_by_id(self, project_id, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = 'workspaces/{}/projects/{}/'.format(
            workspace_id, project_id
        )
        time_check(self)
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )

        return response.json()

    def get_tags(self, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = 'workspaces/{}/tags/'.format(workspace_id)
        time_check(self)
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )

        return {
            tag["name"]: tag["id"] for tag in response.json()
        }

    def get_tasks(self, project_id, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = 'workspaces/{}/projects/{}/tasks/'.format(
            workspace_id, project_id
        )
        time_check(self)
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )

        return {
            task["name"]: task["id"] for task in response.json()
        }

    def get_workspace_id(self, workspace_name):
        all_workspaces = self.get_workspaces()
        if workspace_name not in all_workspaces:
            return None
        return all_workspaces[workspace_name]

    def get_project_id(self, project_name, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        all_projects = self.get_projects(workspace_id)
        if project_name not in all_projects:
            return None
        return all_projects[project_name]

    def get_tag_id(self, tag_name, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        all_tasks = self.get_tags(workspace_id)
        if tag_name not in all_tasks:
            return None
        return all_tasks[tag_name]

    def get_task_id(
        self, task_name, project_id, workspace_id=None
    ):
        if workspace_id is None:
            workspace_id = self.workspace_id
        all_tasks = self.get_tasks(
            project_id, workspace_id
        )
        if task_name not in all_tasks:
            return None
        return all_tasks[task_name]

    def get_current_time(self):
        return str(datetime.datetime.utcnow().isoformat())+'Z'

    def start_time_entry(
        self, description, project_id, task_id=None, tag_ids=[],
        workspace_id=None, billable=True
    ):
        # Workspace
        if workspace_id is None:
            workspace_id = self.workspace_id

        # Check if is currently run another times and has same values
        current = self.get_in_progress(workspace_id)
        if current is not None:
            if (
                current.get("description", None) == description and
                current.get("projectId", None) == project_id and
                current.get("taskId", None) == task_id
            ):
                self.bool_timer_run = True
                return self.bool_timer_run
            self.finish_time_entry(workspace_id)

        # Convert billable to strings
        if billable:
            billable = 'true'
        else:
            billable = 'false'
        # Rest API Action
        action_url = 'workspaces/{}/timeEntries/'.format(workspace_id)
        start = self.get_current_time()
        body = {
            "start": start,
            "billable": billable,
            "description": description,
            "projectId": project_id,
            "taskId": task_id,
            "tagIds": tag_ids
        }
        time_check(self)
        response = requests.post(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers,
            json=body
        )

        success = False
        if response.status_code < 300:
            success = True
        return success

    def get_in_progress(self, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = 'workspaces/{}/timeEntries/inProgress'.format(
            workspace_id
        )
        time_check(self)
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )
        try:
            output = response.json()
        except json.decoder.JSONDecodeError:
            output = None
        return output

    def finish_time_entry(self, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        current = self.get_in_progress(workspace_id)
        if current is None:
            return

        current_id = current["id"]
        action_url = 'workspaces/{}/timeEntries/{}'.format(
            workspace_id, current_id
        )
        body = {
            "start": current["timeInterval"]["start"],
            "billable": current["billable"],
            "description": current["description"],
            "projectId": current["projectId"],
            "taskId": current["taskId"],
            "tagIds": current["tagIds"],
            "end": self.get_current_time()
        }
        time_check(self)
        response = requests.put(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers,
            json=body
        )
        return response.json()

    def get_time_entries(
        self, workspace_id=None, quantity=10
    ):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = 'workspaces/{}/timeEntries/'.format(workspace_id)
        time_check(self)
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )
        return response.json()[:quantity]

    def remove_time_entry(self, tid, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = 'workspaces/{}/timeEntries/{}'.format(
            workspace_id, tid
        )
        time_check(self)
        response = requests.delete(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )
        return response.json()

    def add_project(self, name, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = 'workspaces/{}/projects/'.format(workspace_id)
        body = {
            "name": name,
            "clientId": "",
            "isPublic": "false",
            "estimate": {
                "estimate": 0,
                "type": "AUTO"
            },
            "color": "#f44336",
            "billable": "true"
        }
        time_check(self)
        response = requests.post(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers,
            json=body
        )
        return response.json()

    def add_workspace(self, name):
        action_url = 'workspaces/'
        body = {"name": name}
        time_check(self)
        response = requests.post(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers,
            json=body
        )
        return response.json()

    def add_task(
        self, name, project_id, workspace_id=None
    ):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = 'workspaces/{}/projects/{}/tasks/'.format(
            workspace_id, project_id
        )
        body = {
            "name": name,
            "projectId": project_id
        }
        time_check(self)
        response = requests.post(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers,
            json=body
        )
        return response.json()

    def add_tag(self, name, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = 'workspaces/{}/tags'.format(workspace_id)
        body = {
            "name": name
        }
        time_check(self)
        response = requests.post(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers,
            json=body
        )
        return response.json()

    def delete_project(
        self, project_id, workspace_id=None
    ):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = '/workspaces/{}/projects/{}'.format(
            workspace_id, project_id
        )
        time_check(self)
        response = requests.delete(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers,
        )
        return response.json()

    def convert_input(
        self, entity_id, entity_name, mode='Workspace', project_id=None
    ):
        if entity_id is None:
            error = False
            error_msg = 'Missing information "{}"'
            if mode.lower() == 'workspace':
                if entity_id is None and entity_name is None:
                    if self.workspace_id is not None:
                        entity_id = self.workspace_id
                    else:
                        error = True
                else:
                    entity_id = self.get_workspace_id(entity_name)
            else:
                if entity_id is None and entity_name is None:
                    error = True
                elif mode.lower() == 'project':
                    entity_id = self.get_project_id(entity_name)
                elif mode.lower() == 'task':
                    entity_id = self.get_task_id(
                        task_name=entity_name, project_id=project_id
                    )
                else:
                    raise TypeError('Unknown type')
            # Raise error
            if error:
                raise ValueError(error_msg.format(mode))

        return entity_id
