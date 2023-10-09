import os
import json
import getpass

import requests

import pyblish.api

from openpype import AYON_SERVER_ENABLED
from openpype.pipeline import legacy_io
from openpype.pipeline.publish import (
    OpenPypePyblishPluginMixin
)
from openpype.lib import (
    BoolDef,
    NumberDef
)


class FusionSubmitDeadline(
    pyblish.api.InstancePlugin,
    OpenPypePyblishPluginMixin
):
    """Submit current Comp to Deadline

    Renders are submitted to a Deadline Web Service as
    supplied via settings key "DEADLINE_REST_URL".

    """

    label = "Submit Fusion to Deadline"
    order = pyblish.api.IntegratorOrder
    hosts = ["fusion"]
    families = ["render"]
    targets = ["local"]

    # presets
    plugin = None

    priority = 50
    chunk_size = 1
    concurrent_tasks = 1
    group = ""

    @classmethod
    def get_attribute_defs(cls):
        return [
            NumberDef(
                "priority",
                label="Priority",
                default=cls.priority,
                decimals=0
            ),
            NumberDef(
                "chunk",
                label="Frames Per Task",
                default=cls.chunk_size,
                decimals=0,
                minimum=1,
                maximum=1000
            ),
            NumberDef(
                "concurrency",
                label="Concurrency",
                default=cls.concurrent_tasks,
                decimals=0,
                minimum=1,
                maximum=10
            ),
            BoolDef(
                "suspend_publish",
                default=False,
                label="Suspend publish"
            )
        ]

    def process(self, instance):
        if not instance.data.get("farm"):
            self.log.debug("Skipping local instance.")
            return

        attribute_values = self.get_attr_values_from_data(
            instance.data)

        # add suspend_publish attributeValue to instance data
        instance.data["suspend_publish"] = attribute_values[
            "suspend_publish"]

        context = instance.context

        key = "__hasRun{}".format(self.__class__.__name__)
        if context.data.get(key, False):
            return
        else:
            context.data[key] = True

        from openpype.hosts.fusion.api.lib import get_frame_path

        # get default deadline webservice url from deadline module
        deadline_url = instance.context.data["defaultDeadline"]
        # if custom one is set in instance, use that
        if instance.data.get("deadlineUrl"):
            deadline_url = instance.data.get("deadlineUrl")
        assert deadline_url, "Requires Deadline Webservice URL"

        # Collect all saver instances in context that are to be rendered
        saver_instances = []
        for instance in context:
            if instance.data["family"] != "render":
                # Allow only saver family instances
                continue

            if not instance.data.get("publish", True):
                # Skip inactive instances
                continue

            self.log.debug(instance.data["name"])
            saver_instances.append(instance)

        if not saver_instances:
            raise RuntimeError("No instances found for Deadline submission")

        comment = instance.data.get("comment", "")
        deadline_user = context.data.get("deadlineUser", getpass.getuser())

        script_path = context.data["currentFile"]

        for item in context:
            if "workfile" in item.data["families"]:
                msg = "Workfile (scene) must be published along"
                assert item.data["publish"] is True, msg

                template_data = item.data.get("anatomyData")
                rep = item.data.get("representations")[0].get("name")
                template_data["representation"] = rep
                template_data["ext"] = rep
                template_data["comment"] = None
                anatomy_filled = context.data["anatomy"].format(template_data)
                template_filled = anatomy_filled["publish"]["path"]
                script_path = os.path.normpath(template_filled)

                self.log.info(
                    "Using published scene for render {}".format(script_path)
                )

        filename = os.path.basename(script_path)

        # Documentation for keys available at:
        # https://docs.thinkboxsoftware.com
        #    /products/deadline/8.0/1_User%20Manual/manual
        #    /manual-submission.html#job-info-file-options
        payload = {
            "JobInfo": {
                # Top-level group name
                "BatchName": filename,

                # Asset dependency to wait for at least the scene file to sync.
                "AssetDependency0": script_path,

                # Job name, as seen in Monitor
                "Name": filename,

                "Priority": attribute_values.get(
                    "priority", self.priority),
                "ChunkSize": attribute_values.get(
                    "chunk", self.chunk_size),
                "ConcurrentTasks": attribute_values.get(
                    "concurrency",
                    self.concurrent_tasks
                ),

                # User, as seen in Monitor
                "UserName": deadline_user,

                "Pool": instance.data.get("primaryPool"),
                "SecondaryPool": instance.data.get("secondaryPool"),
                "Group": self.group,

                "Plugin": self.plugin,
                "Frames": "{start}-{end}".format(
                    start=int(instance.data["frameStartHandle"]),
                    end=int(instance.data["frameEndHandle"])
                ),

                "Comment": comment,
            },
            "PluginInfo": {
                # Input
                "FlowFile": script_path,

                # Mandatory for Deadline
                "Version": str(instance.data["app_version"]),

                # Render in high quality
                "HighQuality": True,

                # Whether saver output should be checked after rendering
                # is complete
                "CheckOutput": True,

                # Proxy: higher numbers smaller images for faster test renders
                # 1 = no proxy quality
                "Proxy": 1
            },

            # Mandatory for Deadline, may be empty
            "AuxFiles": []
        }

        # Enable going to rendered frames from Deadline Monitor
        for index, instance in enumerate(saver_instances):
            head, padding, tail = get_frame_path(
                instance.data["expectedFiles"][0]
            )
            path = "{}{}{}".format(head, "#" * padding, tail)
            folder, filename = os.path.split(path)
            payload["JobInfo"]["OutputDirectory%d" % index] = folder
            payload["JobInfo"]["OutputFilename%d" % index] = filename

        # Include critical variables with submission
        keys = [
            "FTRACK_API_KEY",
            "FTRACK_API_USER",
            "FTRACK_SERVER",
            "AVALON_PROJECT",
            "AVALON_ASSET",
            "AVALON_TASK",
            "AVALON_APP_NAME",
            "OPENPYPE_DEV",
            "OPENPYPE_LOG_NO_COLORS",
            "IS_TEST"
        ]
        environment = dict({key: os.environ[key] for key in keys
                            if key in os.environ}, **legacy_io.Session)

        # to recognize render jobs
        if AYON_SERVER_ENABLED:
            environment["AYON_BUNDLE_NAME"] = os.environ["AYON_BUNDLE_NAME"]
            render_job_label = "AYON_RENDER_JOB"
        else:
            render_job_label = "OPENPYPE_RENDER_JOB"

        environment[render_job_label] = "1"

        payload["JobInfo"].update({
            "EnvironmentKeyValue%d" % index: "{key}={value}".format(
                key=key,
                value=environment[key]
            ) for index, key in enumerate(environment)
        })

        self.log.debug("Submitting..")
        self.log.debug(json.dumps(payload, indent=4, sort_keys=True))

        # E.g. http://192.168.0.1:8082/api/jobs
        url = "{}/api/jobs".format(deadline_url)
        response = requests.post(url, json=payload)
        if not response.ok:
            raise Exception(response.text)

        # Store the response for dependent job submission plug-ins
        for instance in saver_instances:
            instance.data["deadlineSubmissionJob"] = response.json()
