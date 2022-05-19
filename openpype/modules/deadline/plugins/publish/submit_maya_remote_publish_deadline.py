import os
import requests

from maya import cmds

from openpype.pipeline import legacy_io

import pyblish.api


class MayaSubmitRemotePublishDeadline(pyblish.api.ContextPlugin):
    """Submit Maya scene to perform a local publish in Deadline.

    Publishing in Deadline can be helpful for scenes that publish very slow.
    This way it can process in the background on another machine without the
    Artist having to wait for the publish to finish on their local machine.

    Submission is done through the Deadline Web Service.

    Different from `ProcessSubmittedJobOnFarm` which creates publish job
    depending on metadata json containing context and instance data of
    rendered files.
    """

    label = "Submit Scene to Deadline"
    order = pyblish.api.IntegratorOrder
    hosts = ["maya"]
    families = ["deadline"]

    # custom deadline attributes
    deadline_department = ""
    deadline_pool = ""
    deadline_pool_secondary = ""
    deadline_group = ""
    deadline_chunk_size = 1
    deadline_priority = 50

    def process(self, context):

        # Ensure no errors so far
        assert all(result["success"] for result in context.data["results"]), (
            "Errors found, aborting integration..")

        # Note that `publish` data member might change in the future.
        # See: https://github.com/pyblish/pyblish-base/issues/307
        actives = [i for i in context if i.data["publish"]]
        instance_names = sorted(instance.name for instance in actives)

        if not instance_names:
            self.log.warning("No active instances found. "
                             "Skipping submission..")
            return

        scene = context.data["currentFile"]
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
                "Priority": 50,
                "Name": job_name,
                "UserName": context.data["user"],
                # "Comment": instance.context.data.get("comment", ""),
                # "InitialStatus": state
                "Department": self.deadline_department,
                "ChunkSize": self.deadline_chunk_size,
                "Priority": self.deadline_priority,

                "Group": self.deadline_group,

            },
            "PluginInfo": {

                "Build": None,  # Don't force build
                "StrictErrorChecking": True,
                "ScriptJob": True,

                # Inputs
                "SceneFile": scene,
                "ScriptFilename": "{OPENPYPE_ROOT}/scripts/remote_publish.py",

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
        environment["OPENPYPE_USERNAME"] = context.data["user"]
        environment["OPENPYPE_PUBLISH_JOB"] = "1"
        environment["OPENPYPE_RENDER_JOB"] = "0"
        environment["PYBLISH_ACTIVE_INSTANCES"] = ",".join(instance_names)

        payload["JobInfo"].update({
            "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        })

        self.log.info("Submitting Deadline job ...")
        deadline_url = context.data["defaultDeadline"]
        assert deadline_url, "Requires Deadline Webservice URL"
        url = "{}/api/jobs".format(deadline_url)
        response = requests.post(url, json=payload, timeout=10)
        if not response.ok:
            raise Exception(response.text)
