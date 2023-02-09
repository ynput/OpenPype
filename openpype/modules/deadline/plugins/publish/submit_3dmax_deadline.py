import os
import json
import getpass

import requests
import pyblish.api


from openpype.pipeline import legacy_io


class MaxSubmitRenderDeadline(pyblish.api.InstancePlugin):
    """
    3DMax File Submit Render Deadline

    """

    label = "Submit 3DsMax Render to Deadline"
    order = pyblish.api.IntegratorOrder
    hosts = ["max"]
    families = ["maxrender"]
    targets = ["local"]

    def process(self, instance):
        context = instance.context
        filepath = context.data["currentFile"]
        filename = os.path.basename(filepath)
        comment = context.data.get("comment", "")
        deadline_user = context.data.get("deadlineUser", getpass.getuser())
        jobname = "{0} - {1}".format(filename, instance.name)

        # StartFrame to EndFrame
        frames = "{start}-{end}".format(
            start=int(instance.data["frameStart"]),
            end=int(instance.data["frameEnd"])
        )

        payload = {
            "JobInfo": {
                # Top-level group name
                "BatchName": filename,

                # Job name, as seen in Monitor
                "Name": jobname,

                # Arbitrary username, for visualisation in Monitor
                "UserName": deadline_user,

                "Plugin": instance.data["plugin"],
                "Pool": instance.data.get("primaryPool"),
                "secondaryPool": instance.data.get("secondaryPool"),
                "Frames": frames,
                "ChunkSize": instance.data.get("chunkSize", 10),
                "Comment": comment
            },
            "PluginInfo": {
                # Input
                "SceneFile": instance.data["source"],
                "Version": "2023",
                "SaveFile": True,
                # Mandatory for Deadline
                # Houdini version without patch number

                "IgnoreInputs": True
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }
        # Include critical environment variables with submission + api.Session
        keys = [
            # Submit along the current Avalon tool setup that we launched
            # this application with so the Render Slave can build its own
            # similar environment using it, e.g. "maya2018;vray4.x;yeti3.1.9"
            "AVALON_TOOLS",
            "OPENPYPE_VERSION"
        ]
        # Add mongo url if it's enabled
        if context.data.get("deadlinePassMongoUrl"):
            keys.append("OPENPYPE_MONGO")

        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **legacy_io.Session)

        payload["JobInfo"].update({
            "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        })

        # Include OutputFilename entries
        # The first entry also enables double-click to preview rendered
        # frames from Deadline Monitor
        output_data = {}
        # need to be fixed
        for i, filepath in enumerate(instance.data["files"]):
            dirname = os.path.dirname(filepath)
            fname = os.path.basename(filepath)
            output_data["OutputDirectory%d" % i] = dirname.replace("\\", "/")
            output_data["OutputFilename%d" % i] = fname

        if not os.path.exists(dirname):
            self.log.info("Ensuring output directory exists: %s" %
                          dirname)
            os.makedirs(dirname)

        payload["JobInfo"].update(output_data)

        self.submit(instance, payload)

    def submit(self, instance, payload):

        context = instance.context
        deadline_url = context.data.get("defaultDeadline")
        deadline_url = instance.data.get(
            "deadlineUrl", deadline_url)

        assert deadline_url, "Requires Deadline Webservice URL"

        plugin = payload["JobInfo"]["Plugin"]
        self.log.info("Using Render Plugin : {}".format(plugin))

        self.log.info("Submitting..")
        self.log.debug(json.dumps(payload, indent=4, sort_keys=True))

        # E.g. http://192.168.0.1:8082/api/jobs
        url = "{}/api/jobs".format(deadline_url)
        response = requests.post(url, json=payload)
        if not response.ok:
            raise Exception(response.text)
        # Store output dir for unified publisher (filesequence)
        expected_files = instance.data["files"]
        self.log.info("exp:{}".format(expected_files))
        output_dir = os.path.dirname(expected_files[0])
        instance.data["outputDir"] = output_dir
        instance.data["deadlineSubmissionJob"] = response.json()
