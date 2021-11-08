"""
Requires:
    CollectPublishedFiles
    CollectModules

Provides:
    Instance
"""
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

        collected_data = collect_scene_data_command.result()
        layers_data = collected_data["layers_data"]
        groups_data = collected_data["groups_data"]
        scene_data = collected_data["scene_data"]
        exposure_frames_by_layer_id = (
            collected_data["exposure_frames_by_layer_id"]
        )
        pre_post_beh_by_layer_id = (
            collected_data["pre_post_beh_by_layer_id"]
        )

        # Store results
        # scene data store the same way as TVPaint collector
        instance.data["sceneData"] = {
            "sceneWidth": scene_data["width"],
            "sceneHeight": scene_data["height"],
            "scenePixelAspect": scene_data["pixel_aspect"],
            "sceneFps": scene_data["fps"],
            "sceneFieldOrder": scene_data["field_order"],
            "sceneMarkIn": scene_data["mark_in"],
            # scene_data["mark_in_state"],
            "sceneMarkInState": scene_data["mark_in_set"],
            "sceneMarkOut": scene_data["mark_out"],
            # scene_data["mark_out_state"],
            "sceneMarkOutState": scene_data["mark_out_set"],
            "sceneStartFrame": scene_data["start_frame"],
            "sceneBgColor": scene_data["bg_color"]
        }
        # Store only raw data
        instance.data["groupsData"] = groups_data
        instance.data["layersData"] = layers_data
        instance.data["layersExposureFrames"] = exposure_frames_by_layer_id
        instance.data["layersPrePostBehavior"] = pre_post_beh_by_layer_id
