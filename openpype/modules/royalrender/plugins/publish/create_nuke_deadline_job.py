# -*- coding: utf-8 -*-
"""Submitting render job to RoyalRender."""
import os
import sys
import re
import platform
from datetime import datetime

from pyblish.api import InstancePlugin, IntegratorOrder, Context
from openpype.tests.lib import is_in_tests
from openpype.lib import is_running_from_build
from openpype.pipeline.publish.lib import get_published_workfile_instance
from openpype.pipeline.publish import KnownPublishError
from openpype.modules.royalrender.api import Api as rrApi
from openpype.modules.royalrender.rr_job import (
    RRJob, CustomAttribute, get_rr_platform)
from openpype.lib import (
    is_running_from_build,
    BoolDef,
    NumberDef
)
from openpype.pipeline import OpenPypePyblishPluginMixin
from openpype.pipeline.farm.tools import iter_expected_files


class CreateNukeRoyalRenderJob(InstancePlugin, OpenPypePyblishPluginMixin):
    label = "Create Nuke Render job in RR"
    order = IntegratorOrder + 0.1
    hosts = ["nuke"]
    families = ["render", "prerender"]
    targets = ["local"]
    optional = True

    priority = 50
    chunk_size = 1
    concurrent_tasks = 1

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
            )
        ]

    def __init__(self, *args, **kwargs):
        self._instance = None
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
                 "You need to configure RoyalRender module."))

        self.rr_api = rrApi(self._rr_root)

        self.scene_path = context.data["currentFile"]
        if self.use_published:
            file_path = get_published_workfile_instance(context)

            # fallback if nothing was set
            if not file_path:
                self.log.warning("Falling back to workfile")
                file_path = context.data["currentFile"]

            self.scene_path = file_path
            self.log.info(
                "Using published scene for render {}".format(self.scene_path)
            )

        if not self._instance.data.get("expectedFiles"):
            self._instance.data["expectedFiles"] = []

        if not self._instance.data.get("rrJobs"):
            self._instance.data["rrJobs"] = []

        self._instance.data["rrJobs"] += self.create_jobs()

        # redefinition of families
        if "render" in self._instance.data["family"]:
            self._instance.data["family"] = "write"
            self._instance.data["families"].insert(0, "render2d")
        elif "prerender" in self._instance.data["family"]:
            self._instance.data["family"] = "write"
            self._instance.data["families"].insert(0, "prerender")

        self._instance.data["outputDir"] = os.path.dirname(
            self._instance.data["path"]).replace("\\", "/")


    def create_jobs(self):
        submit_frame_start = int(self._instance.data["frameStartHandle"])
        submit_frame_end = int(self._instance.data["frameEndHandle"])

        # get output path
        render_path = self._instance.data['path']
        script_path = self.scene_path
        node = self._instance.data["transientData"]["node"]

        # main job
        jobs = [
            self.get_job(
                script_path,
                render_path,
                node.name(),
                submit_frame_start,
                submit_frame_end,
            )
        ]

        for baking_script in self._instance.data.get("bakingNukeScripts", []):
            render_path = baking_script["bakeRenderPath"]
            script_path = baking_script["bakeScriptPath"]
            exe_node_name = baking_script["bakeWriteNodeName"]

            jobs.append(self.get_job(
                script_path,
                render_path,
                exe_node_name,
                submit_frame_start,
                submit_frame_end
            ))

        return jobs

    def get_job(self, script_path, render_path,
                node_name, start_frame, end_frame):
        """Get RR job based on current instance.

        Args:
            script_path (str): Path to Nuke script.
            render_path (str): Output path.
            node_name (str): Name of the render node.
            start_frame (int): Start frame.
            end_frame (int): End frame.

        Returns:
            RRJob: RoyalRender Job instance.

        """
        render_dir = os.path.normpath(os.path.dirname(render_path))
        batch_name = os.path.basename(script_path)
        jobname = "%s - %s" % (batch_name, self._instance.name)
        if is_in_tests():
            batch_name += datetime.now().strftime("%d%m%Y%H%M%S")

        output_filename_0 = self.preview_fname(render_path)

        custom_attributes = []
        if is_running_from_build():
            custom_attributes = [
                CustomAttribute(
                    name="OpenPypeVersion",
                    value=os.environ.get("OPENPYPE_VERSION"))
            ]

        nuke_version = re.search(
            r"\d+\.\d+", self._instance.context.data.get("hostVersion"))

        # this will append expected files to instance as needed.
        expected_files = self.expected_files(
            render_path, start_frame, end_frame)
        self._instance.data["expectedFiles"].extend(expected_files)
        first_file = next(iter_expected_files(expected_files))

        job = RRJob(
            Software="Nuke",
            Renderer="",
            SeqStart=int(start_frame),
            SeqEnd=int(end_frame),
            SeqStep=int(self._instance.data.get("byFrameStep"), 1),
            SeqFileOffset=0,
            Version=nuke_version.group(),
            SceneName=script_path,
            IsActive=True,
            ImageDir=render_dir.replace("\\", "/"),
            ImageFilename="{}.".format(os.path.splitext(first_file)[0]),
            ImageExtension=os.path.splitext(first_file)[1],
            ImagePreNumberLetter=".",
            ImageSingleOutputFile=False,
            SceneOS=get_rr_platform(),
            Layer=node_name,
            SceneDatabaseDir=script_path,
            CustomSHotName=self._instance.context.data["asset"],
            CompanyProjectName=self._instance.context.data["projectName"],
            ImageWidth=self._instance.data["resolutionWidth"],
            ImageHeight=self._instance.data["resolutionHeight"],
            CustomAttributes=custom_attributes
        )

    @staticmethod
    def _resolve_rr_path(context, rr_path_name):
        # type: (Context, str) -> str
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

    def expected_files(self, path, start_frame, end_frame):
        """Get expected files.

        This function generate expected files from provided
        path and start/end frames.

        It was taken from Deadline module, but this should be
        probably handled better in collector to support more
        flexible scenarios.

        Args:
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
            return

        if self._instance.data.get("slate"):
            start_frame -= 1

        expected_files.extend(
            os.path.join(dir_name, (file % i)).replace("\\", "/")
            for i in range(start_frame, (end_frame + 1))
        )
        return expected_files
