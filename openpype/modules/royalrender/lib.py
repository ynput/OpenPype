# -*- coding: utf-8 -*-
"""Submitting render job to RoyalRender."""
import os
import json
import platform
import re
import tempfile
import uuid
from datetime import datetime

import pyblish.api

from openpype.lib import BoolDef, NumberDef, is_running_from_build
from openpype.lib.execute import run_openpype_process
from openpype.modules.royalrender.api import Api as rrApi
from openpype.modules.royalrender.rr_job import (
    CustomAttribute,
    RRJob,
    RREnvList,
    get_rr_platform,
    SubmitterParameter
)
from openpype.pipeline import OpenPypePyblishPluginMixin
from openpype.pipeline.publish import KnownPublishError
from openpype.pipeline.publish.lib import get_published_workfile_instance
from openpype.tests.lib import is_in_tests


class BaseCreateRoyalRenderJob(pyblish.api.InstancePlugin,
                               OpenPypePyblishPluginMixin):
    """Creates separate rendering job for Royal Render"""
    label = "Create Nuke Render job in RR"
    order = pyblish.api.IntegratorOrder + 0.1
    hosts = ["nuke"]
    families = ["render", "prerender"]
    targets = ["local"]
    optional = True

    priority = 50
    chunk_size = 1
    concurrent_tasks = 1
    use_gpu = True
    use_published = True

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
                "use_gpu",
                default=cls.use_gpu,
                label="Use GPU"
            ),
            BoolDef(
                "suspend_publish",
                default=False,
                label="Suspend publish"
            ),
            BoolDef(
                "use_published",
                default=cls.use_published,
                label="Use published workfile"
            )
        ]

    def __init__(self, *args, **kwargs):
        self._rr_root = None
        self.scene_path = None
        self.job = None
        self.submission_parameters = None
        self.rr_api = None

    def process(self, instance):
        if not instance.data.get("farm"):
            self.log.info("Skipping local instance.")
            return

        instance.data["attributeValues"] = self.get_attr_values_from_data(
            instance.data)

        # add suspend_publish attributeValue to instance data
        instance.data["suspend_publish"] = instance.data["attributeValues"][
            "suspend_publish"]

        context = instance.context

        self._rr_root = self._resolve_rr_path(context, instance.data.get(
            "rrPathName"))  # noqa
        self.log.debug(self._rr_root)
        if not self._rr_root:
            raise KnownPublishError(
                ("Missing RoyalRender root. "
                 "Admin needs to configure RoyalRender module in Settings ."))

        self.rr_api = rrApi(self._rr_root)

        self.scene_path = context.data["currentFile"]
        if self.use_published:
            published_workfile = get_published_workfile_instance(context)

            # fallback if nothing was set
            if published_workfile is None:
                self.log.warning("Falling back to workfile")
                file_path = context.data["currentFile"]
            else:
                workfile_repre = published_workfile.data["representations"][0]
                file_path = workfile_repre["published_path"]

            self.scene_path = file_path
            self.log.info(
                "Using published scene for render {}".format(self.scene_path)
            )

        if not instance.data.get("expectedFiles"):
            instance.data["expectedFiles"] = []

        if not instance.data.get("rrJobs"):
            instance.data["rrJobs"] = []

    def get_job(self, instance, script_path, render_path, node_name):
        """Get RR job based on current instance.

        Args:
            script_path (str): Path to Nuke script.
            render_path (str): Output path.
            node_name (str): Name of the render node.

        Returns:
            RRJob: RoyalRender Job instance.

        """
        start_frame = int(instance.data["frameStartHandle"])
        end_frame = int(instance.data["frameEndHandle"])

        batch_name = os.path.basename(script_path)
        jobname = "%s - %s" % (batch_name, instance.name)
        if is_in_tests():
            batch_name += datetime.now().strftime("%d%m%Y%H%M%S")

        render_dir = os.path.normpath(os.path.dirname(render_path))
        output_filename_0 = self.pad_file_name(render_path, str(start_frame))
        file_name, file_ext = os.path.splitext(
            os.path.basename(output_filename_0))

        custom_attributes = []
        if is_running_from_build():
            custom_attributes = [
                CustomAttribute(
                    name="OpenPypeVersion",
                    value=os.environ.get("OPENPYPE_VERSION"))
            ]

        # this will append expected files to instance as needed.
        expected_files = self.expected_files(
            instance, render_path, start_frame, end_frame)
        instance.data["expectedFiles"].extend(expected_files)

        submitter_parameters = []

        anatomy_data = instance.context.data["anatomyData"]
        environment = RREnvList({
            "AVALON_PROJECT": anatomy_data["project"]["name"],
            "AVALON_ASSET": instance.context.data["asset"],
            "AVALON_TASK": anatomy_data["task"]["name"],
            "AVALON_APP_NAME": instance.context.data.get("appName"),
            "AYON_RENDER_JOB": "1",
            "AYON_BUNDLE_NAME": os.environ["AYON_BUNDLE_NAME"]
        })

        render_dir = render_dir.replace("\\", "/")
        job = RRJob(
            Software="",
            Renderer="",
            SeqStart=int(start_frame),
            SeqEnd=int(end_frame),
            SeqStep=int(instance.data.get("byFrameStep", 1)),
            SeqFileOffset=0,
            Version=0,
            SceneName=script_path,
            IsActive=True,
            ImageDir=render_dir,
            ImageFilename=file_name,
            ImageExtension=file_ext,
            ImagePreNumberLetter="",
            ImageSingleOutputFile=False,
            SceneOS=get_rr_platform(),
            Layer=node_name,
            SceneDatabaseDir=script_path,
            CustomSHotName=jobname,
            CompanyProjectName=instance.context.data["projectName"],
            ImageWidth=instance.data["resolutionWidth"],
            ImageHeight=instance.data["resolutionHeight"],
            CustomAttributes=custom_attributes,
            SubmitterParameters=submitter_parameters,
            rrEnvList=environment.serialize(),
            rrEnvFile=os.path.join(render_dir, "rrEnv.rrEenv"),
        )

        return job

    def update_job_with_host_specific(self, instance, job):
        """Host specific mapping for RRJob"""
        raise NotImplementedError

    @staticmethod
    def _resolve_rr_path(context, rr_path_name):
        # type: (pyblish.api.Context, str) -> str
        rr_settings = (
            context.data
            ["system_settings"]
            ["modules"]
            ["royalrender"]
        )
        try:
            default_servers = rr_settings["rr_paths"]
            project_servers = (
                context.data
                ["project_settings"]
                ["royalrender"]
                ["rr_paths"]
            )
            rr_servers = {
                k: default_servers[k]
                for k in project_servers
                if k in default_servers
            }

        except (AttributeError, KeyError):
            # Handle situation were we had only one url for royal render.
            return context.data["defaultRRPath"][platform.system().lower()]

        return rr_servers[rr_path_name][platform.system().lower()]

    def expected_files(self, instance, path, start_frame, end_frame):
        """Get expected files.

        This function generate expected files from provided
        path and start/end frames.

        It was taken from Deadline module, but this should be
        probably handled better in collector to support more
        flexible scenarios.

        Args:
            instance (Instance)
            path (str): Output path.
            start_frame (int): Start frame.
            end_frame (int): End frame.

        Returns:
            list: List of expected files.

        """
        dir_name = os.path.dirname(path)
        file = os.path.basename(path)

        expected_files = []

        if "#" in file:
            pparts = file.split("#")
            padding = "%0{}d".format(len(pparts) - 1)
            file = pparts[0] + padding + pparts[-1]

        if "%" not in file:
            expected_files.append(path)
            return expected_files

        if instance.data.get("slate"):
            start_frame -= 1

        expected_files.extend(
            os.path.join(dir_name, (file % i)).replace("\\", "/")
            for i in range(start_frame, (end_frame + 1))
        )
        return expected_files

    def pad_file_name(self, path, first_frame):
        """Return output file path with #### for padding.

        RR requires the path to be formatted with # in place of numbers.
        For example `/path/to/render.####.png`

        Args:
            path (str): path to rendered image
            first_frame (str): from representation to cleany replace with #
                padding

        Returns:
            str

        """
        self.log.debug("pad_file_name path: `{}`".format(path))
        if "%" in path:
            search_results = re.search(r"(%0)(\d)(d.)", path).groups()
            self.log.debug("_ search_results: `{}`".format(search_results))
            return int(search_results[1])
        if "#" in path:
            self.log.debug("already padded: `{}`".format(path))
            return path

        if first_frame:
            padding = len(first_frame)
            path = path.replace(first_frame, "#" * padding)

        return path
