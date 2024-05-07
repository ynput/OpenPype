# -*- coding: utf-8 -*-
"""Create publishing job on RoyalRender."""
import os
import attr
import json
import re

import pyblish.api

from openpype.modules.royalrender.rr_job import (
    RRJob,
    RREnvList,
    get_rr_platform
)
from openpype.pipeline.publish import KnownPublishError
from openpype.pipeline import (
    legacy_io,
)
from openpype.pipeline.farm.pyblish_functions import (
    create_skeleton_instance,
    create_instances_for_aov,
    attach_instances_to_subset,
    prepare_representations,
    create_metadata_path
)
from openpype.pipeline import publish


class CreatePublishRoyalRenderJob(pyblish.api.InstancePlugin,
                                  publish.ColormanagedPyblishPluginMixin):
    """Creates job which publishes rendered files to publish area.

    Job waits until all rendering jobs are finished, triggers `publish` command
    where it reads from prepared .json file with metadata about what should
    be published, renames prepared images and publishes them.

    When triggered it produces .log file next to .json file in work area.
    """
    label = "Create publish job in RR"
    order = pyblish.api.IntegratorOrder + 0.2
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

    environ_job_filter = [
        "OPENPYPE_METADATA_FILE"
    ]

    environ_keys = [
        "FTRACK_API_USER",
        "FTRACK_API_KEY",
        "FTRACK_SERVER",
        "AVALON_APP_NAME",
        "OPENPYPE_USERNAME",
        "OPENPYPE_SG_USER",
        "AYON_BUNDLE_NAME"
    ]
    priority = 50

    def process(self, instance):
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

        do_not_add_review = False
        if instance.data.get("review") is False:
            self.log.debug("Instance has review explicitly disabled.")
            do_not_add_review = True

        if isinstance(instance.data.get("expectedFiles")[0], dict):
            instances = create_instances_for_aov(
                instance, instance_skeleton_data,
                self.aov_filter, self.skip_integration_repre_list,
                do_not_add_review)

        else:
            representations = prepare_representations(
                instance_skeleton_data,
                instance.data.get("expectedFiles"),
                self.anatomy,
                self.aov_filter,
                self.skip_integration_repre_list,
                do_not_add_review,
                instance.context,
                self
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
                "Can't create publish job without prior rendering jobs first")

        rr_job = self.get_job(instance, instances)
        instance.data["rrJobs"].append(rr_job)

        # publish job file
        publish_job = {
            "asset": instance_skeleton_data["asset"],
            "frameStart": instance_skeleton_data["frameStart"],
            "frameEnd": instance_skeleton_data["frameEnd"],
            "fps": instance_skeleton_data["fps"],
            "source": instance_skeleton_data["source"],
            "user": instance.context.data["user"],
            "version": instance.context.data["version"],   # workfile version
            "intent": instance.context.data.get("intent"),
            "comment": instance.context.data.get("comment"),
            "job": attr.asdict(rr_job),
            "session": legacy_io.Session.copy(),
            "instances": instances
        }

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
        data = instance.data.copy()
        subset = data["subset"]
        jobname = "Publish - {subset}".format(subset=subset)

        # Transfer the environment from the original job to this dependent
        # job, so they use the same environment
        metadata_path, rootless_metadata_path = \
            create_metadata_path(instance, self.anatomy)

        anatomy_data = instance.context.data["anatomyData"]

        environment = RREnvList({
            "AVALON_PROJECT": anatomy_data["project"]["name"],
            "AVALON_ASSET": instance.context.data["asset"],
            "AVALON_TASK": anatomy_data["task"]["name"],
            "OPENPYPE_USERNAME": anatomy_data["user"]
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
                if len(job.rrEnvList) > 2000:
                    self.log.warning(("Job environment is too long "
                                      f"{len(job.rrEnvList)} > 2000"))
                job_environ.update(
                    dict(RREnvList.parse(job.rrEnvList))
                )
            jobs_pre_ids.append(job.PreID)

        for env_j_key in self.environ_job_filter:
            if job_environ.get(env_j_key):
                environment[env_j_key] = job_environ[env_j_key]

        priority = self.priority or instance.data.get("priority", 50)

        # rr requires absolut path or all jobs won't show up in rControl
        abs_metadata_path = self.anatomy.fill_root(rootless_metadata_path)

        # command line set in E01__OpenPype__PublishJob.cfg, here only
        # additional logging
        args = [
            ">", os.path.join(os.path.dirname(abs_metadata_path),
                              "rr_out.log"),
            "2>&1"
        ]

        job = RRJob(
            Software="AYON",
            Renderer="Once",
            SeqStart=1,
            SeqEnd=1,
            SeqStep=1,
            SeqFileOffset=0,
            Version=os.environ["AYON_BUNDLE_NAME"],
            SceneName=abs_metadata_path,
            # command line arguments
            CustomAddCmdFlags=" ".join(args),
            IsActive=True,
            ImageFilename="execOnce.file",
            ImageDir="<SceneFolder>",
            ImageExtension="",
            ImagePreNumberLetter="",
            SceneOS=get_rr_platform(),
            rrEnvList=environment.serialize(),
            Priority=priority,
            CustomSHotName=jobname,
            CompanyProjectName=instance.context.data["projectName"]
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
