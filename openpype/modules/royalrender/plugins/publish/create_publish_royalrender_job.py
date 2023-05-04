# -*- coding: utf-8 -*-
"""Create publishing job on RoyalRender."""
import os
from copy import deepcopy
import json

from pyblish.api import InstancePlugin, IntegratorOrder, Instance

from openpype.pipeline import legacy_io
from openpype.modules.royalrender.rr_job import RRJob, RREnvList
from openpype.pipeline.publish import KnownPublishError
from openpype.lib.openpype_version import (
    get_OpenPypeVersion, get_openpype_version)
from openpype.pipeline.farm.pyblish_functions import (
    create_skeleton_instance,
    create_instances_for_aov,
    attach_instances_to_subset,
    prepare_representations,
    create_metadata_path
)


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

    skip_integration_repre_list = []

    # mapping of instance properties to be transferred to new instance
    #     for every specified family
    instance_transfer = {
        "slate": ["slateFrames", "slate"],
        "review": ["lutPath"],
        "render2d": ["bakingNukeScripts", "version"],
        "renderlayer": ["convertToScanline"]
    }

    # list of family names to transfer to new family if present
    families_transfer = ["render3d", "render2d", "ftrack", "slate"]

    def process(self, instance):
        # data = instance.data.copy()
        context = instance.context
        self.context = context
        self.anatomy = instance.context.data["anatomy"]

        if not instance.data.get("farm"):
            self.log.info("Skipping local instance.")
            return

        instance_skeleton_data = create_skeleton_instance(
            instance,
            families_transfer=self.families_transfer,
            instance_transfer=self.instance_transfer)

        if isinstance(instance.data.get("expectedFiles")[0], dict):
            instances = create_instances_for_aov(
                instance, instance_skeleton_data,
                self.aov_filter, self.skip_integration_repre_list)

        else:
            representations = prepare_representations(
                instance_skeleton_data,
                instance.data.get("expectedFiles"),
                self.anatomy,
                self.aov_filter,
                self.skip_integration_repre_list
            )

            if "representations" not in instance_skeleton_data.keys():
                instance_skeleton_data["representations"] = []

            # add representation
            instance_skeleton_data["representations"] += representations
            instances = [instance_skeleton_data]

        # attach instances to subset
        if instance.data.get("attachTo"):
            instances = attach_instances_to_subset(
                instance.data.get("attachTo"), instances
            )

        self.log.info("Creating RoyalRender Publish job ...")

        if not instance.data.get("rrJobs"):
            self.log.error(("There is no prior RoyalRender "
                            "job on the instance."))
            raise KnownPublishError(
                "Can't create publish job without prior ppducing jobs first")

        publish_job = self.get_job(instance, instances)

        instance.data["rrJobs"] += publish_job

        metadata_path, rootless_metadata_path = \
            create_metadata_path(instance, self.anatomy)

        self.log.info("Writing json file: {}".format(metadata_path))
        with open(metadata_path, "w") as f:
            json.dump(publish_job, f, indent=4, sort_keys=True)

    def get_job(self, instance, instances):
        """Create RR publishing job.

        Based on provided original instance and additional instances,
        create publishing job and return it to be submitted to farm.

        Args:
            instance (Instance): Original instance.
            instances (list of Instance): List of instances to
                be published on farm.

        Returns:
            RRJob: RoyalRender publish job.

        """
        # data = deepcopy(instance.data)
        data = instance.data
        subset = data["subset"]
        job_name = "Publish - {subset}".format(subset=subset)

        instance_version = instance.data.get("version")  # take this if exists
        override_version = instance_version if instance_version != 1 else None

        # Transfer the environment from the original job to this dependent
        # job, so they use the same environment
        metadata_path, roothless_metadata_path = \
            create_metadata_path(instance, self.anatomy)

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
        for job in instance.data["rrJobs"]:  # type: RRJob
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

        openpype_version = get_OpenPypeVersion()
        current_version = openpype_version(version=get_openpype_version())
        job = RRJob(
            Software="OpenPype",
            Renderer="Once",
            # path to OpenPype
            SeqStart=1,
            SeqEnd=1,
            SeqStep=1,
            SeqFileOffset=0,
            Version="{}.{}".format(
                current_version.major(), current_version.minor()),
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

        return job
