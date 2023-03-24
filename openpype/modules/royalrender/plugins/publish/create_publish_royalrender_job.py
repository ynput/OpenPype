# -*- coding: utf-8 -*-
"""Create publishing job on RoyalRender."""
from pyblish.api import InstancePlugin, IntegratorOrder
from copy import deepcopy
from openpype.pipeline import legacy_io
import requests
import os

from openpype.modules.royalrender.rr_job import RRJob, RREnvList
from openpype.pipeline.publish import KnownPublishError
from openpype.modules.royalrender.api import Api as rrApi


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
        # data = instance.data.copy()
        context = instance.context
        self.context = context
        self.anatomy = instance.context.data["anatomy"]

        # asset = data.get("asset")
        # subset = data.get("subset")
        # source = self._remap_source(
        #   data.get("source") or context.data["source"])

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

    def get_job(self, instance, job, instances):
        """Submit publish job to RoyalRender."""
        data = instance.data.copy()
        subset = data["subset"]
        job_name = "Publish - {subset}".format(subset=subset)

        override_version = None
        instance_version = instance.data.get("version")  # take this if exists
        if instance_version != 1:
            override_version = instance_version
        output_dir = self._get_publish_folder(
            instance.context.data['anatomy'],
            deepcopy(instance.data["anatomyData"]),
            instance.data.get("asset"),
            instances[0]["subset"],
            # TODO: this shouldn't be hardcoded and is in fact settable by
            #       Settings.
            'render',
            override_version
        )

        # Transfer the environment from the original job to this dependent
        # job, so they use the same environment
        metadata_path, roothless_metadata_path = \
            self._create_metadata_path(instance)

        environment = RREnvList({
            "AVALON_PROJECT": legacy_io.Session["AVALON_PROJECT"],
            "AVALON_ASSET": legacy_io.Session["AVALON_ASSET"],
            "AVALON_TASK": legacy_io.Session["AVALON_TASK"],
            "OPENPYPE_USERNAME": instance.context.data["user"],
            "OPENPYPE_PUBLISH_JOB": "1",
            "OPENPYPE_RENDER_JOB": "0",
            "OPENPYPE_REMOTE_JOB": "0",
            "OPENPYPE_LOG_NO_COLORS": "1"
        })

        # add environments from self.environ_keys
        for env_key in self.environ_keys:
            if os.getenv(env_key):
                environment[env_key] = os.environ[env_key]

        # pass environment keys from self.environ_job_filter
        # and collect all pre_ids to wait for
        job_environ = {}
        jobs_pre_ids = []
        for job in instance["rrJobs"]:  # type: RRJob
            if job.rrEnvList:
                job_environ.update(
                    dict(RREnvList.parse(job.rrEnvList))
                )
            jobs_pre_ids.append(job.PreID)

        for env_j_key in self.environ_job_filter:
            if job_environ.get(env_j_key):
                environment[env_j_key] = job_environ[env_j_key]

        # Add mongo url if it's enabled
        if instance.context.data.get("deadlinePassMongoUrl"):
            mongo_url = os.environ.get("OPENPYPE_MONGO")
            if mongo_url:
                environment["OPENPYPE_MONGO"] = mongo_url

        priority = self.priority or instance.data.get("priority", 50)

        args = [
            "--headless",
            'publish',
            roothless_metadata_path,
            "--targets", "deadline",
            "--targets", "farm"
        ]

        job = RRJob(
            Software="OpenPype",
            Renderer="Once",
            # path to OpenPype
            SeqStart=1,
            SeqEnd=1,
            SeqStep=1,
            SeqFileOffset=0,
            Version=os.environ.get("OPENPYPE_VERSION"),
            # executable
            SceneName=roothless_metadata_path,
            # command line arguments
            CustomAddCmdFlags=" ".join(args),
            IsActive=True,
            ImageFilename="execOnce.file",
            ImageDir="<SceneFolder>",
            ImageExtension="",
            ImagePreNumberLetter="",
            SceneOS=RRJob.get_rr_platform(),
            rrEnvList=environment.serialize(),
            Priority=priority
        )

        # add assembly jobs as dependencies
        if instance.data.get("tileRendering"):
            self.log.info("Adding tile assembly jobs as dependencies...")
            job.WaitForPreIDs += instance.data.get("assemblySubmissionJobs")
        elif instance.data.get("bakingSubmissionJobs"):
            self.log.info("Adding baking submission jobs as dependencies...")
            job.WaitForPreIDs += instance.data["bakingSubmissionJobs"]
        else:
            job.WaitForPreIDs += jobs_pre_ids

        self.log.info("Creating RoyalRender Publish job ...")

        if not instance.data.get("rrJobs"):
            self.log.error("There is no RoyalRender job on the instance.")
            raise KnownPublishError(
                "Can't create publish job without producing jobs")

        instance.data["rrJobs"] += job
