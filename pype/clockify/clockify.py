import os
import requests
import json
import datetime
import appdirs


class ClockifyAPI:
    endpoint = "https://api.clockify.me/api/"
    headers = {"X-Api-Key": None}
    app_dir = os.path.normpath(appdirs.user_data_dir('pype-app', 'pype'))
    file_name = 'clockify.json'
    fpath = os.path.join(app_dir, file_name)
    workspace = None

    def __init__(self, workspace=None, debug=False):
        self.debug = debug
        self.set_api()
        if workspace is not None:
            self.set_workspace(workspace)

    def set_api(self):
        api_key = self.get_api_key()
        if api_key is not None:
            self.headers["X-Api-Key"] = api_key
            return

        raise ValueError('Api key is not set')

    def set_workspace(self, name):
        all_workspaces = self.get_workspaces()
        if name in all_workspaces:
            self.workspace = name
            return

    def get_api_key(self):
        credentials = None
        try:
            file = open(self.fpath, 'r')
            credentials = json.load(file).get('api_key', None)
        except Exception:
            file = open(self.fpath, 'w')
        file.close()
        return credentials

    def get_workspaces(self):
        action_url = 'workspaces/'
        response = requests.get(
            self.endpoint + action_url,
            headers=self.headers
        )
        return {
            workspace["name"]: workspace["id"] for workspace in response.json()
        }

    def get_projects(self, workspace=None):
        if workspace is None:
            workspace = self.workspace
        action_url = 'workspaces/{}/projects/'.format(workspace)
        response = requests.get(
            self.endpoint + action_url,
            headers=self.headers
        )

        return {
            project["name"]: project["id"] for project in response.json()
        }

    def print_json(self, inputjson):
        print(json.dumps(inputjson, indent=2))

    def get_current_time(self):
        return str(datetime.datetime.utcnow().isoformat())+'Z'

    def start_time_entry(
        self, description, project_id, task_id, billable="true", workspace=None
    ):
        if workspace is None:
            workspace = self.workspace
        action_url = 'workspaces/{}/timeEntries/'.format(workspace)
        start = self.get_current_time()
        body = {
            "start": start,
            "billable": billable,
            "description": description,
            "projectId": project_id,
            "taskId": task_id,
            "tagIds": None
        }
        response = requests.post(
            self.endpoint + action_url,
            headers=self.headers,
            json=body
        )
        return response.json()

    def get_in_progress(self, workspace=None):
        if workspace is None:
            workspace = self.workspace
        action_url = 'workspaces/{}/timeEntries/inProgress'.format(workspace)
        response = requests.get(
            self.endpoint + action_url,
            headers=self.headers
        )
        return response.json()

    def finish_time_entry(self, workspace=None):
        if workspace is None:
            workspace = self.workspace
        current = self.get_in_progress(workspace)
        current_id = current["id"]
        action_url = 'workspaces/{}/timeEntries/{}'.format(
            workspace, current_id
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
        response = requests.put(
            self.endpoint + action_url,
            headers=self.headers,
            json=body
        )
        return response.json()

    def get_time_entries(self, workspace=None):
        if workspace is None:
            workspace = self.workspace
        action_url = 'workspaces/{}/timeEntries/'.format(workspace)
        response = requests.get(
            self.endpoint + action_url,
            headers=self.headers
        )
        return response.json()[:10]

    def remove_time_entry(self, tid, workspace=None):
        if workspace is None:
            workspace = self.workspace
        action_url = 'workspaces/{}/timeEntries/{tid}'.format(workspace)
        response = requests.delete(
            self.endpoint + action_url,
            headers=self.headers
        )
        return response.json()

    def add_project(self, name, workspace=None):
        if workspace is None:
            workspace = self.workspace
        action_url = 'workspaces/{}/projects/'.format(workspace)
        body = {
            "name": name,
            "clientId": "",
            "isPublic": "false",
            "estimate": None,
            "color": None,
            "billable": None
        }
        response = requests.post(
            self.endpoint + action_url,
            headers=self.headers,
            json=body
        )
        return response.json()

    def add_workspace(self, name):
        action_url = 'workspaces/'
        body = {"name": name}
        response = requests.post(
            self.endpoint + action_url,
            headers=self.headers,
            json=body
        )
        return response.json()


def main():
    clockify = ClockifyAPI()
    from pprint import pprint
    pprint(clockify.get_workspaces())


if __name__ == "__main__":
    main()
