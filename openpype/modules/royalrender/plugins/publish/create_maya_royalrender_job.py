# -*- coding: utf-8 -*-
"""Submitting render job to RoyalRender."""
import os
import sys
import platform

from maya.OpenMaya import MGlobal  # noqa
from pyblish.api import InstancePlugin, IntegratorOrder, Context
from openpype.pipeline.publish.lib import get_published_workfile_instance
from openpype.pipeline.publish import KnownPublishError
from openpype.modules.royalrender.api import Api as rrApi
from openpype.modules.royalrender.rr_job import RRJob


class CreateMayaRoyalRenderJob(InstancePlugin):
    label = "Create Maya Render job in RR"
    order = IntegratorOrder + 0.1
    families = ["renderlayer"]
    targets = ["local"]
    use_published = True

    def __init__(self, *args, **kwargs):
        self._instance = None
        self._rrRoot = None
        self.scene_path = None
        self.job = None
        self.submission_parameters = None
        self.rr_api = None

    def get_job(self):
        """Prepare job payload.

        Returns:
            RRJob: RoyalRender job payload.
        """
        def get_rr_platform():
            if sys.platform.lower() in ["win32", "win64"]:
                return "windows"
            elif sys.platform.lower() == "darwin":
                return "mac"
            else:
                return "linux"

        expected_files = self._instance.data["expectedFiles"]
        first_file = next(self._iter_expected_files(expected_files))
        output_dir = os.path.dirname(first_file)
        self._instance.data["outputDir"] = output_dir
        workspace = self._instance.context.data["workspaceDir"]
        default_render_file = (
            self._instance.context.data
            ['project_settings']
            ['maya']
            ['RenderSettings']
            ['default_render_image_folder']
        )
        # file_name = os.path.basename(self.scene_path)
        dir_name = os.path.join(workspace, default_render_file)
        layer = self._instance.data["setMembers"]  # type: str
        layer_name = layer.removeprefix("rs_")

        job = RRJob(
            Software="Maya",
            Renderer=self._instance.data["renderer"],
            SeqStart=int(self._instance.data["frameStartHandle"]),
            SeqEnd=int(self._instance.data["frameEndHandle"]),
            SeqStep=int(self._instance.data["byFrameStep"]),
            SeqFileOffset=0,
            Version="{0:.2f}".format(MGlobal.apiVersion() / 10000),
            SceneName=self.scene_path,
            IsActive=True,
            ImageDir=dir_name,
            ImageFilename="{}.".format(layer_name),
            ImageExtension=os.path.splitext(first_file)[1],
            ImagePreNumberLetter=".",
            ImageSingleOutputFile=False,
            SceneOS=get_rr_platform(),
            Camera=self._instance.data["cameras"][0],
            Layer=layer_name,
            SceneDatabaseDir=workspace,
            CustomSHotName=self._instance.context.data["asset"],
            CompanyProjectName=self._instance.context.data["projectName"],
            ImageWidth=self._instance.data["resolutionWidth"],
            ImageHeight=self._instance.data["resolutionHeight"],
        )
        return job

    def process(self, instance):
        """Plugin entry point."""
        self._instance = instance
        context = instance.context

        self._rr_root = self._resolve_rr_path(context, instance.data.get("rrPathName"))  # noqa
        self.log.debug(self._rr_root)
        if not self._rr_root:
            raise KnownPublishError(
                ("Missing RoyalRender root. "
                 "You need to configure RoyalRender module."))

        self.rr_api = rrApi(self._rr_root)

        file_path = None
        if self.use_published:
            file_path = get_published_workfile_instance(context)

            # fallback if nothing was set
            if not file_path:
                self.log.warning("Falling back to workfile")
                file_path = context.data["currentFile"]

            self.scene_path = file_path

        self._instance.data["rrJobs"] = [self.get_job()]

    @staticmethod
    def _iter_expected_files(exp):
        if isinstance(exp[0], dict):
            for _aov, files in exp[0].items():
                for file in files:
                    yield file
        else:
            for file in exp:
                yield file

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
