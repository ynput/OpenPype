import os
import re
import time
import json
import datetime
import requests
from .constants import (
    CLOCKIFY_ENDPOINT,
    ADMIN_PERMISSION_NAMES,
    MAX_CALLS,
    PERIOD
)

from openpype.lib.local_settings import OpenPypeSecureRegistry
from ratelimiter import RateLimiter


class ClockifyAPI:
    def __init__(self, api_key=None, master_parent=None):
        self.workspace_name = None
        self.workspace_id = None
        self.master_parent = master_parent
        self.api_key = api_key
        self.request_counter = 0
        self.request_time = time.time()
        self._secure_registry = None
        self.user_id = None

    @property
    def secure_registry(self):
        if self._secure_registry is None:
            self._secure_registry = OpenPypeSecureRegistry("clockify")
        return self._secure_registry

    @property
    def headers(self):
        return {"x-api-key": self.api_key}

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
            self.set_user_id()
            if self.master_parent:
                self.master_parent.signed_in()
            return True
        return False

    # @RateLimiter(MAX_CALLS, PERIOD)
    def validate_api_key(self, api_key):
        test_headers = {'x-api-key': api_key}
        action_url = 'user'
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=test_headers
        )
        if response.status_code != 200:
            return False
        return True

    # @RateLimiter(MAX_CALLS, PERIOD)
    def validate_workspace_perm(self, workspace_id=None):
        print("validating workspace")
        user_id = self.user_id
        if user_id is None:
            print("no User found during validation")
            return False
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = "workspaces/{}/users/{}/roles".format(
            workspace_id, user_id
        )
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )
        user_roles = response.json()
        for perm in user_roles:
            if perm['name'] in ADMIN_PERMISSION_NAMES:
                return True
        return False

    @RateLimiter(MAX_CALLS, PERIOD)
    def get_user_id(self):
        action_url = 'user'
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )
        result = response.json()
        user_id = result.get("id", None)

        print(f"User: {user_id}")
        return user_id

    def set_workspace(self, name=None):
        if name is None:
            name = os.environ.get('CLOCKIFY_WORKSPACE', None)
        self.workspace_name = name
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

    def set_user_id(self):
        try:
            result = self.validate_user_id()
        except Exception:
            result = False
        if result is not False:
            self.user_id = result

    def validate_user_id(self):
        user_id = self.get_user_id()
        return user_id or False
        
    def get_api_key(self):
        return self.secure_registry.get_item("api_key", None)

    def save_api_key(self, api_key):
        self.secure_registry.set_item("api_key", api_key)

    # @RateLimiter(MAX_CALLS, PERIOD)
    def get_workspaces(self):
        action_url = 'workspaces/'
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )
        return {
            workspace["name"]: workspace["id"] for workspace in response.json()
        }

    # @RateLimiter(MAX_CALLS, PERIOD)
    def get_projects(self, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = f"workspaces/{workspace_id}/projects"
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )
        result = response.json()
        
        print(f"projects: {response.json()}")
        
        if result.get("code") == 1000:
            return None
        return {
            project["name"]: project["id"] for project in result
        }

    @RateLimiter(MAX_CALLS, PERIOD)
    def get_project_by_id(self, project_id, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = 'workspaces/{}/projects/{}/'.format(
            workspace_id, project_id
        )

        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )

        return response.json()

    # @RateLimiter(MAX_CALLS, PERIOD)
    def get_tags(self, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = 'workspaces/{}/tags/'.format(workspace_id)
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )

        return {
            tag["name"]: tag["id"] for tag in response.json()
        }

    # @RateLimiter(MAX_CALLS, PERIOD)
    def get_tasks(self, project_id, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = 'workspaces/{}/projects/{}/tasks/'.format(
            workspace_id, project_id
        )
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

    # @RateLimiter(MAX_CALLS, PERIOD)
    def start_time_entry(
        self, description, project_id, task_id=None, tag_ids=[],
        workspace_id=None, user_id=None, billable=True
    ):
        # Workspace
        if workspace_id is None:
            workspace_id = self.workspace_id
        if user_id is None:
            user_id = self.user_id
        print(f"Starting timer: {user_id}: {workspace_id}")

        # Check if is currently run another times and has same values
        current = self.get_in_progress(workspace_id)
        if current is not None:
            current = current[0]
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
        action_url = 'workspaces/{}/user/{}time-entries/'.format(
            workspace_id, user_id)
        start = self.get_current_time()
        body = {
            "start": start,
            "billable": billable,
            "description": description,
            "projectId": project_id,
            "taskId": task_id,
            "tagIds": tag_ids
        }
        response = requests.post(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers,
            json=body
        )
        print(f"RESPONSE: {response}")
        success = False
        if response.status_code < 300:
            success = True
        return success

    @RateLimiter(MAX_CALLS, PERIOD)
    def get_in_progress(self, user_id=None, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        if user_id is None:
            user_id = self.user_id

        action_url = (f'workspaces/{workspace_id}/user/'
                     f'{user_id}/time-entries?in-progress=1')
        print(action_url)
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
            )
        try:
            output = response.json()
        except json.decoder.JSONDecodeError:
            output = None
        if isinstance(output, dict):
            print(f"Response code: {output.get('code')}")
            output = None
        return output

    def finish_time_entry(self, user_id=None, workspace_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        if user_id is None:
            user_id = self.user_id
        current = self.get_in_progress(workspace_id)
        if current is None:
            print("no current")
            return

        current_id = current[0]["id"]
        action_url = 'workspaces/{}/user/{}/time-entries/{}'.format(
            workspace_id, user_id, current_id
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

    # @RateLimiter(MAX_CALLS, PERIOD)
    def get_time_entries(
        self, workspace_id=None, user_id=None, quantity=10
    ):
        if workspace_id is None:
            workspace_id = self.workspace_id
        if user_id is None:
            user_id = self.user_id
        action_url = 'workspaces/{}/user/{}/time-entries/'.format(
            workspace_id, user_id)
        response = requests.get(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )
        return response.json()[:quantity]

    # @RateLimiter(MAX_CALLS, PERIOD)
    def remove_time_entry(self, tid, workspace_id=None, user_id=None):
        if workspace_id is None:
            workspace_id = self.workspace_id
        action_url = 'workspaces/{}/user/{}/time-entries/{}'.format(
            workspace_id, user_id, tid
        )
        response = requests.delete(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers
        )
        return response.json()

    # @RateLimiter(MAX_CALLS, PERIOD)
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
        response = requests.post(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers,
            json=body
        )
        return response.json()

    # @RateLimiter(MAX_CALLS, PERIOD)
    def add_workspace(self, name):
        action_url = 'workspaces/'
        body = {"name": name}
        response = requests.post(
            CLOCKIFY_ENDPOINT + action_url,
            headers=self.headers,
            json=body
        )
        return response.json()

    # @RateLimiter(MAX_CALLS, PERIOD)
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
