import os
import json
import getpass

from avalon import api
from avalon.vendor import requests

import pyblish.api


class FusionSubmitDeadline(pyblish.api.InstancePlugin):
    """Submit current Comp to Deadline

    Renders are submitted to a Deadline Web Service as
    supplied via the environment variable DEADLINE_REST_URL

    """

    label = "Submit to Deadline"
    order = pyblish.api.IntegratorOrder
    hosts = ["fusion"]
    families = ["saver.deadline"]

    def process(self, instance):
        instance.data["toBeRenderedOn"] = "deadline"
        context = instance.context

        key = "__hasRun{}".format(self.__class__.__name__)
        if context.data.get(key, False):
            return
        else:
            context.data[key] = True

        from avalon.fusion.lib import get_frame_path

        DEADLINE_REST_URL = api.Session.get("DEADLINE_REST_URL",
                                          "http://localhost:8082")
        assert DEADLINE_REST_URL, "Requires DEADLINE_REST_URL"

        # Collect all saver instances in context that are to be rendered
        saver_instances = []
        for instance in context[:]:
            if not self.families[0] in instance.data.get("families"):
                # Allow only saver family instances
                continue

            if not instance.data.get("publish", True):
                # Skip inactive instances
                continue
            self.log.debug(instance.data["name"])
            saver_instances.append(instance)

        if not saver_instances:
            raise RuntimeError("No instances found for Deadline submittion")

        fusion_version = int(context.data["fusionVersion"])
        filepath = context.data["currentFile"]
        filename = os.path.basename(filepath)
        comment = context.data.get("comment", "")
        deadline_user = context.data.get("deadlineUser", getpass.getuser())

        # Documentation for keys available at:
        # https://docs.thinkboxsoftware.com
        #    /products/deadline/8.0/1_User%20Manual/manual
        #    /manual-submission.html#job-info-file-options
        payload = {
            "JobInfo": {
                # Top-level group name
                "BatchName": filename,

                # Asset dependency to wait for at least the scene file to sync.
                "AssetDependency0": filepath,

                # Job name, as seen in Monitor
                "Name": filename,

                # User, as seen in Monitor
                "UserName": deadline_user,

                # Use a default submission pool for Fusion
                "Pool": "fusion",

                "Plugin": "Fusion",
                "Frames": "{start}-{end}".format(
                    start=int(context.data["frameStart"]),
                    end=int(context.data["frameEnd"])
                ),

                "Comment": comment,
            },
            "PluginInfo": {
                # Input
                "FlowFile": filepath,

                # Mandatory for Deadline
                "Version": str(fusion_version),

                # Render in high quality
                "HighQuality": True,

                # Whether saver output should be checked after rendering
                # is complete
                "CheckOutput": True,

                # Proxy: higher numbers smaller images for faster test renders
                # 1 = no proxy quality
                "Proxy": 1,
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }

        # Enable going to rendered frames from Deadline Monitor
        for index, instance in enumerate(saver_instances):
            head, padding, tail = get_frame_path(instance.data["path"])
            path = "{}{}{}".format(head, "#" * padding, tail)
            folder, filename = os.path.split(path)
            payload["JobInfo"]["OutputDirectory%d" % index] = folder
            payload["JobInfo"]["OutputFilename%d" % index] = filename

        # Include critical variables with submission
        keys = [
            # TODO: This won't work if the slaves don't have accesss to
            # these paths, such as if slaves are running Linux and the
            # submitter is on Windows.
            "PYTHONPATH",
            "OFX_PLUGIN_PATH",
            "FUSION9_MasterPrefs"
        ]
        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **api.Session)

        payload["JobInfo"].update({
            "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        })

        self.log.info("Submitting..")
        self.log.info(json.dumps(payload, indent=4, sort_keys=True))

        # E.g. http://192.168.0.1:8082/api/jobs
        url = "{}/api/jobs".format(DEADLINE_REST_URL)
        response = requests.post(url, json=payload)
        if not response.ok:
            raise Exception(response.text)

        # Store the response for dependent job submission plug-ins
        for instance in saver_instances:
            instance.data["deadlineSubmissionJob"] = response.json()
