# -*- coding: utf-8 -*-
"""Submitting render job to RoyalRender."""
import re

from openpype.modules.royalrender import lib


class CreateNukeRoyalRenderJob(lib.BaseCreateRoyalRenderJob):
    """Creates separate rendering job for Royal Render"""
    label = "Create Nuke Render job in RR"
    hosts = ["nuke"]
    families = ["render", "prerender"]

    def process(self, instance):
        super(CreateNukeRoyalRenderJob, self).process(instance)

        # redefinition of families
        if "render" in instance.data["family"]:
            instance.data["family"] = "write"
            instance.data["families"].insert(0, "render2d")
        elif "prerender" in instance.data["family"]:
            instance.data["family"] = "write"
            instance.data["families"].insert(0, "prerender")

        jobs = self.create_jobs(instance)
        for job in jobs:
            job = self.update_job_with_host_specific(instance, job)
            job = self.inject_environment(instance, job)

            instance.data["rrJobs"].append(job)

    def update_job_with_host_specific(self, instance, job):
        nuke_version = re.search(
            r"\d+\.\d+", instance.context.data.get("hostVersion"))

        job.Software = "Nuke"
        job.Version = nuke_version.group()

        return job

    def create_jobs(self, instance):
        """Nuke creates multiple RR jobs - for baking etc."""
        # get output path
        render_path = instance.data['path']
        script_path = self.scene_path
        node = instance.data["transientData"]["node"]

        # main job
        jobs = [
            self.get_job(
                instance,
                script_path,
                render_path,
                node.name()
            )
        ]

        for baking_script in instance.data.get("bakingNukeScripts", []):
            render_path = baking_script["bakeRenderPath"]
            script_path = baking_script["bakeScriptPath"]
            exe_node_name = baking_script["bakeWriteNodeName"]

            jobs.append(self.get_job(
                instance,
                script_path,
                render_path,
                exe_node_name
            ))

        return jobs
