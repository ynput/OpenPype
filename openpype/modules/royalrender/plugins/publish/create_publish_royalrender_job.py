# -*- coding: utf-8 -*-
"""Create publishing job on RoyalRender."""
from pyblish.api import InstancePlugin, IntegratorOrder
from copy import deepcopy
from openpype.pipeline import legacy_io
import requests
import os


class CreatePublishRoyalRenderJob(InstancePlugin):
    label = "Create publish job in RR"
    order = IntegratorOrder + 0.2
    icon = "tractor"
    targets = ["local"]
    hosts = ["fusion", "maya", "nuke", "celaction", "aftereffects", "harmony"]
    families = ["render.farm", "prerender.farm",
                "renderlayer", "imagesequence", "vrayscene"]
    aov_filter = {"maya": [r".*([Bb]eauty).*"],
                  "aftereffects": [r".*"],  # for everything from AE
                  "harmony": [r".*"],  # for everything from AE
                  "celaction": [r".*"]}

    def process(self, instance):
        data = instance.data.copy()
        context = instance.context
        self.context = context
        self.anatomy = instance.context.data["anatomy"]

        asset = data.get("asset")
        subset = data.get("subset")
        source = self._remap_source(
            data.get("source") or context.data["source"])



    def _remap_source(self, source):
        success, rootless_path = (
            self.anatomy.find_root_template_from_path(source)
        )
        if success:
            source = rootless_path
        else:
            # `rootless_path` is not set to `source` if none of roots match
            self.log.warning((
                "Could not find root path for remapping \"{}\"."
                " This may cause issues."
            ).format(source))
        return source

    def _submit_post_job(self, instance, job, instances):
        """Submit publish job to RoyalRender."""
        data = instance.data.copy()
        subset = data["subset"]
        job_name = "Publish - {subset}".format(subset=subset)

        # instance.data.get("subset") != instances[0]["subset"]
        # 'Main' vs 'renderMain'
        override_version = None
        instance_version = instance.data.get("version")  # take this if exists
        if instance_version != 1:
            override_version = instance_version
        output_dir = self._get_publish_folder(
            instance.context.data['anatomy'],
            deepcopy(instance.data["anatomyData"]),
            instance.data.get("asset"),
            instances[0]["subset"],
            'render',
            override_version
        )

        # Transfer the environment from the original job to this dependent
        # job, so they use the same environment
        metadata_path, roothless_metadata_path = \
            self._create_metadata_path(instance)

        environment = {
            "AVALON_PROJECT": legacy_io.Session["AVALON_PROJECT"],
            "AVALON_ASSET": legacy_io.Session["AVALON_ASSET"],
            "AVALON_TASK": legacy_io.Session["AVALON_TASK"],
            "OPENPYPE_USERNAME": instance.context.data["user"],
            "OPENPYPE_PUBLISH_JOB": "1",
            "OPENPYPE_RENDER_JOB": "0",
            "OPENPYPE_REMOTE_JOB": "0",
            "OPENPYPE_LOG_NO_COLORS": "1"
        }

        # add environments from self.environ_keys
        for env_key in self.environ_keys:
            if os.getenv(env_key):
                environment[env_key] = os.environ[env_key]

        # pass environment keys from self.environ_job_filter
        job_environ = job["Props"].get("Env", {})
        for env_j_key in self.environ_job_filter:
            if job_environ.get(env_j_key):
                environment[env_j_key] = job_environ[env_j_key]

        # Add mongo url if it's enabled
        if instance.context.data.get("deadlinePassMongoUrl"):
            mongo_url = os.environ.get("OPENPYPE_MONGO")
            if mongo_url:
                environment["OPENPYPE_MONGO"] = mongo_url

        priority = self.deadline_priority or instance.data.get("priority", 50)

        args = [
            "--headless",
            'publish',
            roothless_metadata_path,
            "--targets", "deadline",
            "--targets", "farm"
        ]

        # Generate the payload for Deadline submission
        payload = {
            "JobInfo": {
                "Plugin": self.deadline_plugin,
                "BatchName": job["Props"]["Batch"],
                "Name": job_name,
                "UserName": job["Props"]["User"],
                "Comment": instance.context.data.get("comment", ""),

                "Department": self.deadline_department,
                "ChunkSize": self.deadline_chunk_size,
                "Priority": priority,

                "Group": self.deadline_group,
                "Pool": instance.data.get("primaryPool"),
                "SecondaryPool": instance.data.get("secondaryPool"),

                "OutputDirectory0": output_dir
            },
            "PluginInfo": {
                "Version": self.plugin_pype_version,
                "Arguments": " ".join(args),
                "SingleFrameOnly": "True",
            },
            # Mandatory for Deadline, may be empty
            "AuxFiles": [],
        }

        # add assembly jobs as dependencies
        if instance.data.get("tileRendering"):
            self.log.info("Adding tile assembly jobs as dependencies...")
            job_index = 0
            for assembly_id in instance.data.get("assemblySubmissionJobs"):
                payload["JobInfo"]["JobDependency{}".format(job_index)] = assembly_id  # noqa: E501
                job_index += 1
        elif instance.data.get("bakingSubmissionJobs"):
            self.log.info("Adding baking submission jobs as dependencies...")
            job_index = 0
            for assembly_id in instance.data["bakingSubmissionJobs"]:
                payload["JobInfo"]["JobDependency{}".format(job_index)] = assembly_id  # noqa: E501
                job_index += 1
        else:
            payload["JobInfo"]["JobDependency0"] = job["_id"]

        if instance.data.get("suspend_publish"):
            payload["JobInfo"]["InitialStatus"] = "Suspended"

        for index, (key_, value_) in enumerate(environment.items()):
            payload["JobInfo"].update(
                {
                    "EnvironmentKeyValue%d"
                    % index: "{key}={value}".format(
                        key=key_, value=value_
                    )
                }
            )
        # remove secondary pool
        payload["JobInfo"].pop("SecondaryPool", None)

        self.log.info("Submitting Deadline job ...")

        url = "{}/api/jobs".format(self.deadline_url)
        response = requests.post(url, json=payload, timeout=10)
        if not response.ok:
            raise Exception(response.text)