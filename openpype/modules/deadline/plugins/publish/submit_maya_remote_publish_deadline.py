import os
import requests

from maya import cmds

from openpype.pipeline import legacy_io
from openpype.settings import get_project_settings

import pyblish.api


class MayaSubmitRemotePublishDeadline(pyblish.api.InstancePlugin):
    """Submit Maya scene to perform a local publish in Deadline.

    Publishing in Deadline can be helpful for scenes that publish very slow.
    This way it can process in the background on another machine without the
    Artist having to wait for the publish to finish on their local machine.

    Submission is done through the Deadline Web Service. DL then triggers
    `openpype/scripts/remote_publish.py`.

    Each publishable instance creates its own full publish job.

    Different from `ProcessSubmittedJobOnFarm` which creates publish job
    depending on metadata json containing context and instance data of
    rendered files.
    """

    label = "Submit Scene to Deadline"
    order = pyblish.api.IntegratorOrder
    hosts = ["maya"]
    families = ["deadline"]

    def process(self, instance):
        settings = get_project_settings(os.getenv("AVALON_PROJECT"))
        # use setting for publish job on farm, no reason to have it separately
        deadline_publish_job_sett = (settings["deadline"]
                                     ["publish"]
                                     ["ProcessSubmittedJobOnFarm"])

        # Ensure no errors so far
        assert (all(result["success"]
                    for result in instance.context.data["results"]),
                    ("Errors found, aborting integration.."))

        if not instance.data["publish"]:
            self.log.warning("No active instances found. "
                             "Skipping submission..")
            return

        scene = instance.context.data["currentFile"]
        scenename = os.path.basename(scene)

        # Get project code
        project_name = legacy_io.Session["AVALON_PROJECT"]

        job_name = "{scene} [PUBLISH]".format(scene=scenename)
        batch_name = "{code} - {scene}".format(code=project_name,
                                               scene=scenename)

        # Generate the payload for Deadline submission
        payload = {
            "JobInfo": {
                "Plugin": "MayaBatch",
                "BatchName": batch_name,
                "Name": job_name,
                "UserName": instance.context.data["user"],
                "Comment": instance.context.data.get("comment", ""),
                # "InitialStatus": state
                "Department": deadline_publish_job_sett["deadline_department"],
                "ChunkSize": deadline_publish_job_sett["deadline_chunk_size"],
                "Priority": deadline_publish_job_sett["deadline_priority"],
                "Group": deadline_publish_job_sett["deadline_group"],
                "Pool": deadline_publish_job_sett["deadline_pool"],
            },
            "PluginInfo": {

                "Build": None,  # Don't force build
                "StrictErrorChecking": True,
                "ScriptJob": True,

                # Inputs
                "SceneFile": scene,
                "ScriptFilename": "{OPENPYPE_REPOS_ROOT}/openpype/scripts/remote_publish.py",   # noqa

                # Mandatory for Deadline
                "Version": cmds.about(version=True),

                # Resolve relative references
                "ProjectPath": cmds.workspace(query=True,
                                              rootDirectory=True),

            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }

        # Include critical environment variables with submission + api.Session
        keys = [
            "FTRACK_API_USER",
            "FTRACK_API_KEY",
            "FTRACK_SERVER"
        ]
        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **legacy_io.Session)

        # TODO replace legacy_io with context.data ?
        environment["AVALON_PROJECT"] = legacy_io.Session["AVALON_PROJECT"]
        environment["AVALON_ASSET"] = legacy_io.Session["AVALON_ASSET"]
        environment["AVALON_TASK"] = legacy_io.Session["AVALON_TASK"]
        environment["AVALON_APP_NAME"] = os.environ.get("AVALON_APP_NAME")
        environment["OPENPYPE_LOG_NO_COLORS"] = "1"
        environment["OPENPYPE_REMOTE_JOB"] = "1"
        environment["OPENPYPE_USERNAME"] = instance.context.data["user"]
        environment["OPENPYPE_PUBLISH_SUBSET"] = instance.data["subset"]

        payload["JobInfo"].update({
            "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        })

        self.log.info("Submitting Deadline job ...")
        deadline_url = instance.context.data["defaultDeadline"]
        # if custom one is set in instance, use that
        if instance.data.get("deadlineUrl"):
            deadline_url = instance.data.get("deadlineUrl")
        assert deadline_url, "Requires Deadline Webservice URL"
        url = "{}/api/jobs".format(deadline_url)
        response = requests.post(url, json=payload, timeout=10)
        if not response.ok:
            raise Exception(response.text)
