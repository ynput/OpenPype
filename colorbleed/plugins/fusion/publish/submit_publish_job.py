import os
import json

from avalon import api
from avalon.vendor import requests

import pyblish.api


def _get_script():
    """Get path to the image sequence script"""
    try:
        from colorbleed.scripts import publish_imagesequence
    except Exception as e:
        raise RuntimeError("Expected module 'publish_imagesequence'"
                           "to be available")

    module_path = publish_imagesequence.__file__
    if module_path.endswith(".pyc"):
        module_path = module_path[:-len(".pyc")] + ".py"

    return module_path


class SubmitDependentImageSequenceJobDeadline(pyblish.api.InstancePlugin):
    """Submit image sequence publish jobs to Deadline.

    These jobs are dependent on a deadline job submission prior to this
    plug-in.

    Renders are submitted to a Deadline Web Service as
    supplied via the environment variable AVALON_DEADLINE

    Requires:
        - instance.data["deadlineSubmission"]
        - instance.data["outputDir"]

    Optional:
        - instance.data["publishJobState"] (str): "Active" or "Suspended"
            defaults to "Suspended"

    """

    label = "Submit image sequence jobs to Deadline"
    order = pyblish.api.IntegratorOrder + 0.1
    hosts = ["fusion"]
    families = ["colorbleed.saver"]

    def process(self, instance):

        AVALON_DEADLINE = api.Session.get("AVALON_DEADLINE",
                                          "http://localhost:8082")
        assert AVALON_DEADLINE, "Requires AVALON_DEADLINE"

        # Get a submission job
        job = instance.data.get("deadlineSubmissionJob")
        if not job:
            raise RuntimeError("Can't continue without valid deadline "
                               "submission prior to this plug-in.")

        state = instance.data.get("publishJobState", "Suspended")
        job_name = "{batch} - {subset} [publish image sequence]".format(
            batch=job["Props"]["Name"],
            subset=instance.data["subset"]
        )
        output_dir = instance.data["outputDir"]

        # Write metadata for publish job
        data = instance.data.copy()
        data.pop("deadlineSubmissionJob")
        metadata = {
            "instance": data,
            "jobs": [job],
            "session": api.Session.copy()
        }
        metadata_filename = "{}_metadata.json".format(instance.data["subset"])
        metadata_path = os.path.join(output_dir, metadata_filename)
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4, sort_keys=True)

        # Generate the payload for Deadline submission
        payload = {
            "JobInfo": {
                "Plugin": "Python",
                "BatchName": job["Props"]["Batch"],
                "Name": job_name,
                "JobType": "Normal",
                "JobDependency0": job["_id"],
                "UserName": job["Props"]["User"],
                "Comment": instance.context.data.get("comment", ""),
                "InitialStatus": state
            },
            "PluginInfo": {
                "Version": "3.6",
                "ScriptFile": _get_script(),
                "Arguments": '--path "{}"'.format(metadata_path),
                "SingleFrameOnly": "True"
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }

        self.log.info("Submitting..")
        self.log.info(json.dumps(payload, indent=4, sort_keys=True))

        url = "{}/api/jobs".format(AVALON_DEADLINE)
        response = requests.post(url, json=payload)
        if not response.ok:
            raise Exception(response.text)
