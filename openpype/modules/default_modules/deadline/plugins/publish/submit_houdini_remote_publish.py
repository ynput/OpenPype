import os
import json

import requests
import hou

from avalon import api, io

import pyblish.api


class HoudiniSubmitPublishDeadline(pyblish.api.ContextPlugin):
    """Submit Houdini scene to perform a local publish in Deadline.

    Publishing in Deadline can be helpful for scenes that publish very slow.
    This way it can process in the background on another machine without the
    Artist having to wait for the publish to finish on their local machine.

    Submission is done through the Deadline Web Service as
    supplied via the environment variable AVALON_DEADLINE.

    """

    label = "Submit Scene to Deadline"
    order = pyblish.api.IntegratorOrder
    hosts = ["houdini"]
    families = ["*"]
    targets = ["deadline"]

    def process(self, context):

        # Ensure no errors so far
        assert all(
            result["success"] for result in context.data["results"]
        ), "Errors found, aborting integration.."

        # Deadline connection
        AVALON_DEADLINE = api.Session.get(
            "AVALON_DEADLINE", "http://localhost:8082"
        )
        assert AVALON_DEADLINE, "Requires AVALON_DEADLINE"

        # Note that `publish` data member might change in the future.
        # See: https://github.com/pyblish/pyblish-base/issues/307
        actives = [i for i in context if i.data["publish"]]
        instance_names = sorted(instance.name for instance in actives)

        if not instance_names:
            self.log.warning(
                "No active instances found. " "Skipping submission.."
            )
            return

        scene = context.data["currentFile"]
        scenename = os.path.basename(scene)

        # Get project code
        project = io.find_one({"type": "project"})
        code = project["data"].get("code", project["name"])

        job_name = "{scene} [PUBLISH]".format(scene=scenename)
        batch_name = "{code} - {scene}".format(code=code, scene=scenename)
        deadline_user = "roy"  # todo: get deadline user dynamically

        # Get only major.minor version of Houdini, ignore patch version
        version = hou.applicationVersionString()
        version = ".".join(version.split(".")[:2])

        # Generate the payload for Deadline submission
        payload = {
            "JobInfo": {
                "Plugin": "Houdini",
                "Pool": "houdini",  # todo: remove hardcoded pool
                "BatchName": batch_name,
                "Comment": context.data.get("comment", ""),
                "Priority": 50,
                "Frames": "1-1",  # Always trigger a single frame
                "IsFrameDependent": False,
                "Name": job_name,
                "UserName": deadline_user,
                # "Comment": instance.context.data.get("comment", ""),
                # "InitialStatus": state
            },
            "PluginInfo": {
                "Build": None,  # Don't force build
                "IgnoreInputs": True,
                # Inputs
                "SceneFile": scene,
                "OutputDriver": "/out/REMOTE_PUBLISH",
                # Mandatory for Deadline
                "Version": version,
            },
            # Mandatory for Deadline, may be empty
            "AuxFiles": [],
        }

        # Process submission per individual instance if the submission
        # is set to publish each instance as a separate job. Else submit
        # a single job to process all instances.
        per_instance = context.data.get("separateJobPerInstance", False)
        if per_instance:
            # Submit a job per instance
            job_name = payload["JobInfo"]["Name"]
            for instance in instance_names:
                # Clarify job name per submission (include instance name)
                payload["JobInfo"]["Name"] = job_name + " - %s" % instance
                self.submit_job(
                    context,
                    payload,
                    instances=[instance],
                    deadline=AVALON_DEADLINE
                )
        else:
            # Submit a single job
            self.submit_job(
                context,
                payload,
                instances=instance_names,
                deadline=AVALON_DEADLINE
            )

    def submit_job(self, context, payload, instances, deadline):

        # Ensure we operate on a copy, a shallow copy is fine.
        payload = payload.copy()

        # Include critical environment variables with submission + api.Session
        keys = [
            # Submit along the current Avalon tool setup that we launched
            # this application with so the Render Slave can build its own
            # similar environment using it, e.g. "houdini17.5;pluginx2.3"
            "AVALON_TOOLS",
        ]
        # Add mongo url if it's enabled
        if context.data.get("deadlinePassMongoUrl"):
            keys.append("OPENPYPE_MONGO")

        environment = dict(
            {key: os.environ[key] for key in keys if key in os.environ},
            **api.Session
        )
        environment["PYBLISH_ACTIVE_INSTANCES"] = ",".join(instances)

        payload["JobInfo"].update(
            {
                "EnvironmentKeyValue%d"
                % index: "{key}={value}".format(
                    key=key, value=environment[key]
                )
                for index, key in enumerate(environment)
            }
        )

        # Submit
        self.log.info("Submitting..")
        self.log.debug(json.dumps(payload, indent=4, sort_keys=True))

        # E.g. http://192.168.0.1:8082/api/jobs
        url = "{}/api/jobs".format(deadline)
        response = requests.post(url, json=payload)
        if not response.ok:
            raise Exception(response.text)
