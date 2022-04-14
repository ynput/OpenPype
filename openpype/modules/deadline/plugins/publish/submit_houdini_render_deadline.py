import os
import json
import getpass

import requests
import pyblish.api

import hou

from openpype.pipeline import legacy_io


class HoudiniSubmitRenderDeadline(pyblish.api.InstancePlugin):
    """Submit Solaris USD Render ROPs to Deadline.

    Renders are submitted to a Deadline Web Service as
    supplied via the environment variable AVALON_DEADLINE.

    Target "local":
        Even though this does *not* render locally this is seen as
        a 'local' submission as it is the regular way of submitting
        a Houdini render locally.

    """

    label = "Submit Render to Deadline"
    order = pyblish.api.IntegratorOrder
    hosts = ["houdini"]
    families = ["usdrender",
                "redshift_rop"]
    targets = ["local"]

    def process(self, instance):

        context = instance.context
        code = context.data["code"]
        filepath = context.data["currentFile"]
        filename = os.path.basename(filepath)
        comment = context.data.get("comment", "")
        deadline_user = context.data.get("deadlineUser", getpass.getuser())
        jobname = "%s - %s" % (filename, instance.name)

        # Support code prefix label for batch name
        batch_name = filename
        if code:
            batch_name = "{0} - {1}".format(code, batch_name)

        # Output driver to render
        driver = instance[0]

        # StartFrame to EndFrame by byFrameStep
        frames = "{start}-{end}x{step}".format(
            start=int(instance.data["frameStart"]),
            end=int(instance.data["frameEnd"]),
            step=int(instance.data["byFrameStep"]),
        )

        # Documentation for keys available at:
        # https://docs.thinkboxsoftware.com
        #    /products/deadline/8.0/1_User%20Manual/manual
        #    /manual-submission.html#job-info-file-options
        payload = {
            "JobInfo": {
                # Top-level group name
                "BatchName": batch_name,

                # Job name, as seen in Monitor
                "Name": jobname,

                # Arbitrary username, for visualisation in Monitor
                "UserName": deadline_user,

                "Plugin": "Houdini",
                "Pool": "houdini_redshift",  # todo: remove hardcoded pool
                "Frames": frames,

                "ChunkSize": instance.data.get("chunkSize", 10),

                "Comment": comment
            },
            "PluginInfo": {
                # Input
                "SceneFile": filepath,
                "OutputDriver": driver.path(),

                # Mandatory for Deadline
                # Houdini version without patch number
                "Version": hou.applicationVersionString().rsplit(".", 1)[0],

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
        for i, filepath in enumerate(instance.data["files"]):
            dirname = os.path.dirname(filepath)
            fname = os.path.basename(filepath)
            output_data["OutputDirectory%d" % i] = dirname.replace("\\", "/")
            output_data["OutputFilename%d" % i] = fname

            # For now ensure destination folder exists otherwise HUSK
            # will fail to render the output image. This is supposedly fixed
            # in new production builds of Houdini
            # TODO Remove this workaround with Houdini 18.0.391+
            if not os.path.exists(dirname):
                self.log.info("Ensuring output directory exists: %s" %
                              dirname)
                os.makedirs(dirname)

        payload["JobInfo"].update(output_data)

        self.submit(instance, payload)

    def submit(self, instance, payload):

        AVALON_DEADLINE = legacy_io.Session.get("AVALON_DEADLINE",
                                          "http://localhost:8082")
        assert AVALON_DEADLINE, "Requires AVALON_DEADLINE"

        plugin = payload["JobInfo"]["Plugin"]
        self.log.info("Using Render Plugin : {}".format(plugin))

        self.log.info("Submitting..")
        self.log.debug(json.dumps(payload, indent=4, sort_keys=True))

        # E.g. http://192.168.0.1:8082/api/jobs
        url = "{}/api/jobs".format(AVALON_DEADLINE)
        response = requests.post(url, json=payload)
        if not response.ok:
            raise Exception(response.text)

        # Store output dir for unified publisher (filesequence)
        output_dir = os.path.dirname(instance.data["files"][0])
        instance.data["outputDir"] = output_dir
        instance.data["deadlineSubmissionJob"] = response.json()
