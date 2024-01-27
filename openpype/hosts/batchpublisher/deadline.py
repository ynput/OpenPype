

import json
import getpass
import os
import requests

from openpype.pipeline import legacy_io
from openpype.lib import is_running_from_build


# Default Deadline job
DEFAULT_PRIORITY = 50
DEFAULT_CHUNK_SIZE = 9999
DEAFAULT_CONCURRENT_TASKS = 1


def payload_submit(
    project_name,
    plugin,
    plugin_data,
    batch_name,
    task_name,
    group="",
    comment="",
    priority=DEFAULT_PRIORITY,
    chunk_size=DEFAULT_CHUNK_SIZE,
    concurrent_tasks=DEAFAULT_CONCURRENT_TASKS,
    frame_range=None,
    department="",
    extra_env=None,
    response_data=None,
):
    if not response_data:
        response_data = {}

    frames = "0" if not frame_range else f"{frame_range[0]}-{frame_range[1]}"

    payload = {
        "JobInfo": {
            # Top-level group name
            "BatchName": batch_name,
            # Job name, as seen in Monitor
            "Name": task_name,
            # Arbitrary username, for visualisation in Monitor
            "UserName": getpass.getuser(),
            "Priority": priority,
            "ChunkSize": chunk_size,
            "ConcurrentTasks": concurrent_tasks,
            "Department": department,
            "Pool": "",
            "SecondaryPool": "",
            "Group": group,
            "Plugin": plugin,
            "Frames": frames,
            "Comment": comment or "",
            # Optional, enable double-click to preview rendered
            # frames from Deadline Monitor
            # "OutputFilename0": preview_fname(render_path).replace("\\", "/"),
        },
        "PluginInfo": plugin_data,
        # Mandatory for Deadline, may be empty
        "AuxFiles": [],
    }

    if response_data.get("_id"):
        payload["JobInfo"].update(
            {
                "JobType": "Normal",
                "BatchName": response_data["Props"]["Batch"],
                "JobDependency0": response_data["_id"],
                "ChunkSize": 99999999,
            }
        )

    # Include critical environment variables with submission
    keys = [
        "AVALON_ASSET",
        "AVALON_TASK",
        "AVALON_PROJECT",
        "AVALON_APP_NAME",
        "OCIO",
        "USER",
        "OPENPYPE_SG_USER",
    ]

    # Add OpenPype version if we are running from build.
    if is_running_from_build():
        keys.append("OPENPYPE_VERSION")

    environment = dict(
        {key: os.environ[key] for key in keys if key in os.environ},
        **legacy_io.Session,
    )

    if extra_env:
        environment.update(extra_env)

    payload["JobInfo"].update(
        {
            "EnvironmentKeyValue%d"
            % index: "{key}={value}".format(
                key=key, value=environment[key]
            )
            for index, key in enumerate(environment)
        }
    )

    plugin = payload["JobInfo"]["Plugin"]
    print("using render plugin : {}".format(plugin))

    print("Submitting..")
    print(json.dumps(payload, indent=4, sort_keys=True))

    # # Deadline connection
    # AVALON_DEADLINE = legacy_io.Session.get(
    #         "AVALON_DEADLINE", "http://localhost:8082")

    DEADLINE_URL = get_deadline_web_service_url(project_name)

    DEADLINE_URL = "http://0.0.0.0:8082"
    url = "{}/api/jobs".format(DEADLINE_URL)
    response = requests.post(url, json=payload, timeout=10)

    if not response.ok:
        raise Exception(response.text)

    return response.json()


def get_deadline_web_service_url(project_name):
    from openpype.settings import (
        get_project_settings,
        get_system_settings)
    from openpype import AYON_SERVER_ENABLED
    project_settings = get_project_settings(project_name)
    # Get deadline settings for project from global project settings
    deadline_settings = project_settings["deadline"]
    # Get deadline settings for context in collector plugin
    # # deadline_settings = context.data["project_settings"]["deadline"]
    deadline_server_name = None
    if AYON_SERVER_ENABLED:
        deadline_server_name = deadline_settings["deadline_server"]
    else:
        deadline_servers = deadline_settings["deadline_servers"]
        if deadline_servers:
            deadline_server_name = deadline_servers[0]
    deadline_webservice_url = None
    for settings in get_system_settings(project_name)["deadline"]["deadline_urls"]:
        if settings["name"] == deadline_server_name:
            deadline_webservice_url = settings["value"]
    return deadline_webservice_url