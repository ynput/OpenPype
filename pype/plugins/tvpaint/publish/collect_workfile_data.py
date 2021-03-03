import os
import json

import pyblish.api
import avalon.api
from avalon.tvpaint import pipeline, lib


class ResetTVPaintWorkfileMetadata(pyblish.api.Action):
    """Fix invalid metadata in workfile."""
    label = "Reset invalid workfile metadata"
    on = "failed"

    def process(self, context, plugin):
        metadata_keys = {
            pipeline.SECTION_NAME_CONTEXT: {},
            pipeline.SECTION_NAME_INSTANCES: [],
            pipeline.SECTION_NAME_CONTAINERS: []
        }
        for metadata_key, default in metadata_keys.items():
            json_string = pipeline.get_workfile_metadata_string(metadata_key)
            if not json_string:
                continue

            try:
                return json.loads(json_string)
            except Exception:
                self.log.warning(
                    (
                        "Couldn't parse metadata from key \"{}\"."
                        " Will reset to default value \"{}\"."
                        " Loaded value was: {}"
                    ).format(metadata_key, default, json_string),
                    exc_info=True
                )
                pipeline.write_workfile_metadata(metadata_key, default)


class CollectWorkfileData(pyblish.api.ContextPlugin):
    label = "Collect Workfile Data"
    order = pyblish.api.CollectorOrder - 1.01
    hosts = ["tvpaint"]
    actions = [ResetTVPaintWorkfileMetadata]

    def process(self, context):
        current_project_id = lib.execute_george("tv_projectcurrentid")
        lib.execute_george("tv_projectselect {}".format(current_project_id))

        # Collect and store current context to have reference
        current_context = {
            "project": avalon.api.Session["AVALON_PROJECT"],
            "asset": avalon.api.Session["AVALON_ASSET"],
            "task": avalon.api.Session["AVALON_TASK"]
        }
        context.data["previous_context"] = current_context
        self.log.debug("Current context is: {}".format(current_context))

        # Collect context from workfile metadata
        self.log.info("Collecting workfile context")
        workfile_context = pipeline.get_current_workfile_context()
        if workfile_context:
            # Change current context with context from workfile
            key_map = (
                ("AVALON_ASSET", "asset"),
                ("AVALON_TASK", "task")
            )
            for env_key, key in key_map:
                avalon.api.Session[env_key] = workfile_context[key]
                os.environ[env_key] = workfile_context[key]
        else:
            # Handle older workfiles or workfiles without metadata
            self.log.warning(
                "Workfile does not contain information about context."
                " Using current Session context."
            )
            workfile_context = current_context.copy()

        context.data["workfile_context"] = workfile_context
        self.log.info("Context changed to: {}".format(workfile_context))

        # Collect instances
        self.log.info("Collecting instance data from workfile")
        instance_data = pipeline.list_instances()
        context.data["workfileInstances"] = instance_data
        self.log.debug(
            "Instance data:\"{}".format(json.dumps(instance_data, indent=4))
        )

        # Collect information about layers
        self.log.info("Collecting layers data from workfile")
        layers_data = lib.layers_data()
        layers_by_name = {}
        for layer in layers_data:
            layer_name = layer["name"]
            if layer_name not in layers_by_name:
                layers_by_name[layer_name] = []
            layers_by_name[layer_name].append(layer)
        context.data["layersData"] = layers_data
        context.data["layersByName"] = layers_by_name

        self.log.debug(
            "Layers data:\"{}".format(json.dumps(layers_data, indent=4))
        )

        # Collect information about groups
        self.log.info("Collecting groups data from workfile")
        group_data = lib.groups_data()
        context.data["groupsData"] = group_data
        self.log.debug(
            "Group data:\"{}".format(json.dumps(group_data, indent=4))
        )

        self.log.info("Collecting scene data from workfile")
        workfile_info_parts = lib.execute_george("tv_projectinfo").split(" ")

        _frame_start = int(workfile_info_parts.pop(-1))
        field_order = workfile_info_parts.pop(-1)
        frame_rate = float(workfile_info_parts.pop(-1))
        pixel_apsect = float(workfile_info_parts.pop(-1))
        height = int(workfile_info_parts.pop(-1))
        width = int(workfile_info_parts.pop(-1))
        workfile_path = " ".join(workfile_info_parts).replace("\"", "")

        frame_start, frame_end = self.collect_clip_frames()
        scene_data = {
            "currentFile": workfile_path,
            "sceneWidth": width,
            "sceneHeight": height,
            "pixelAspect": pixel_apsect,
            "frameStart": frame_start,
            "frameEnd": frame_end,
            "fps": frame_rate,
            "fieldOrder": field_order
        }
        self.log.debug(
            "Scene data: {}".format(json.dumps(scene_data, indent=4))
        )
        context.data.update(scene_data)

    def collect_clip_frames(self):
        clip_info_str = lib.execute_george("tv_clipinfo")
        self.log.debug("Clip info: {}".format(clip_info_str))
        clip_info_items = clip_info_str.split(" ")
        # Color index
        color_idx = clip_info_items.pop(-1)
        clip_info_items.pop(-1)

        mark_out = int(clip_info_items.pop(-1)) + 1
        clip_info_items.pop(-1)

        mark_in = int(clip_info_items.pop(-1)) + 1
        clip_info_items.pop(-1)

        return mark_in, mark_out
