"""
Requires:
    CollectPublishedFiles
    CollectModules

Provides:
    Instance
"""
import json
import time
import pyblish.api
from openpype.hosts.tvpaint.worker import (
    SenderTVPaintCommands,
    CollectSceneData
)


class CollectTVPaintWorkfileData(pyblish.api.InstancePlugin):
    label = "Collect TVPaint Workfile data"
    order = pyblish.api.CollectorOrder + 0.1
    hosts = ["webpublisher"]
    # TODO add families filter

    def process(self, instance):
        # TODO change 'tvpaint_workfile' this is just dummy access
        workfile = instance.data["tvpaint_workfile"]
        # Get JobQueue module
        modules = instance.context.data["openPypeModules"]
        job_queue_module = modules["job_queue"]

        # Prepare tvpaint command
        collect_scene_data_command = CollectSceneData()
        # Create TVPaint sender commands
        commands = SenderTVPaintCommands(workfile, job_queue_module)
        commands.add_command(collect_scene_data_command)

        # Send job and wait for answer
        commands.send_job_and_wait()

        # Store result
        instance.data["sceneData"] = collect_scene_data_command.result()
