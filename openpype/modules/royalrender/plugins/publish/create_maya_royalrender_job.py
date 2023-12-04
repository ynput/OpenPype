# -*- coding: utf-8 -*-
"""Submitting render job to RoyalRender."""
import os

from maya.OpenMaya import MGlobal  # noqa: F401

from openpype.modules.royalrender import lib
from openpype.pipeline.farm.tools import iter_expected_files


class CreateMayaRoyalRenderJob(lib.BaseCreateRoyalRenderJob):
    label = "Create Maya Render job in RR"
    hosts = ["maya"]
    families = ["renderlayer"]

    def update_job_with_host_specific(self, instance, job):
        job.Software = "Maya"
        job.Version = "{0:.2f}".format(MGlobal.apiVersion() / 10000)
        if instance.data.get("cameras"):
            job.Camera = instance.data["cameras"][0].replace("'", '"')
        workspace = instance.context.data["workspaceDir"]
        job.SceneDatabaseDir = workspace

        return job

    def process(self, instance):
        """Plugin entry point."""
        super(CreateMayaRoyalRenderJob, self).process(instance)

        expected_files = instance.data["expectedFiles"]
        first_file_path = next(iter_expected_files(expected_files))
        output_dir = os.path.dirname(first_file_path)
        instance.data["outputDir"] = output_dir

        layer = instance.data["setMembers"]  # type: str
        layer_name = layer.removeprefix("rs_")

        job = self.get_job(instance, self.scene_path, first_file_path,
                           layer_name)
        job = self.update_job_with_host_specific(instance, job)
        job = self.inject_environment(instance, job)

        instance.data["rrJobs"].append(job)
