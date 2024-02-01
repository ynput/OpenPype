import os
import json
import tempfile

import pyblish.api

from openpype.pipeline import legacy_io
from openpype.hosts.tvpaint.api.lib import (
    execute_george,
    execute_george_through_file,
    get_layers_data,
    get_groups_data,
)
from openpype.hosts.tvpaint.api.pipeline import (
    SECTION_NAME_CONTEXT,
    SECTION_NAME_INSTANCES,
    SECTION_NAME_CONTAINERS,

    get_workfile_metadata_string,
    write_workfile_metadata,
    get_current_workfile_context,
    list_instances,
)


class ResetTVPaintWorkfileMetadata(pyblish.api.Action):
    """Fix invalid metadata in workfile."""
    label = "Reset invalid workfile metadata"
    on = "failed"

    def process(self, context, plugin):
        metadata_keys = {
            SECTION_NAME_CONTEXT: {},
            SECTION_NAME_INSTANCES: [],
            SECTION_NAME_CONTAINERS: []
        }
        for metadata_key, default in metadata_keys.items():
            json_string = get_workfile_metadata_string(metadata_key)
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
                write_workfile_metadata(metadata_key, default)


class CollectWorkfileData(pyblish.api.ContextPlugin):
    label = "Collect Workfile Data"
    order = pyblish.api.CollectorOrder - 0.45
    hosts = ["tvpaint"]
    actions = [ResetTVPaintWorkfileMetadata]

    def process(self, context):
        current_project_id = execute_george("tv_projectcurrentid")
        execute_george("tv_projectselect {}".format(current_project_id))

        # Collect and store current context to have reference
        current_context = {
            "project_name": context.data["projectName"],
            "asset_name": context.data["asset"],
            "task_name": context.data["task"]
        }
        self.log.debug("Current context is: {}".format(current_context))

        # Collect context from workfile metadata
        self.log.info("Collecting workfile context")

        workfile_context = get_current_workfile_context()
        if "project" in workfile_context:
            workfile_context = {
                "project_name": workfile_context.get("project"),
                "asset_name": workfile_context.get("asset"),
                "task_name": workfile_context.get("task"),
            }
        # Store workfile context to pyblish context
        context.data["workfile_context"] = workfile_context
        if workfile_context:
            # Change current context with context from workfile
            key_map = (
                ("AVALON_ASSET", "asset_name"),
                ("AVALON_TASK", "task_name")
            )
            for env_key, key in key_map:
                legacy_io.Session[env_key] = workfile_context[key]
                os.environ[env_key] = workfile_context[key]
            self.log.info("Context changed to: {}".format(workfile_context))

            asset_name = workfile_context["asset_name"]
            task_name = workfile_context["task_name"]

        else:
            asset_name = current_context["asset_name"]
            task_name = current_context["task_name"]
            # Handle older workfiles or workfiles without metadata
            self.log.warning((
                "Workfile does not contain information about context."
                " Using current Session context."
            ))

        # Store context asset name
        context.data["asset"] = asset_name
        context.data["task"] = task_name
        self.log.info(
            "Context is set to Asset: \"{}\" and Task: \"{}\"".format(
                asset_name, task_name
            )
        )

        # Collect instances
        self.log.info("Collecting instance data from workfile")
        instance_data = list_instances()
        context.data["workfileInstances"] = instance_data
        self.log.debug(
            "Instance data:\"{}".format(json.dumps(instance_data, indent=4))
        )

        # Collect information about layers
        self.log.info("Collecting layers data from workfile")
        layers_data = get_layers_data()
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
        group_data = get_groups_data()
        context.data["groupsData"] = group_data
        self.log.debug(
            "Group data:\"{}".format(json.dumps(group_data, indent=4))
        )

        self.log.info("Collecting scene data from workfile")
        workfile_info_parts = execute_george("tv_projectinfo").split(" ")

        # Project frame start - not used
        workfile_info_parts.pop(-1)
        field_order = workfile_info_parts.pop(-1)
        frame_rate = float(workfile_info_parts.pop(-1))
        pixel_apsect = float(workfile_info_parts.pop(-1))
        height = int(workfile_info_parts.pop(-1))
        width = int(workfile_info_parts.pop(-1))
        workfile_path = " ".join(workfile_info_parts).replace("\"", "")

        # Marks return as "{frame - 1} {state} ", example "0 set".
        result = execute_george("tv_markin")
        mark_in_frame, mark_in_state, _ = result.split(" ")

        result = execute_george("tv_markout")
        mark_out_frame, mark_out_state, _ = result.split(" ")

        scene_data = {
            "currentFile": workfile_path,
            "sceneWidth": width,
            "sceneHeight": height,
            "scenePixelAspect": pixel_apsect,
            "sceneFps": frame_rate,
            "sceneFieldOrder": field_order,
            "sceneMarkIn": int(mark_in_frame),
            "sceneMarkInState": mark_in_state == "set",
            "sceneMarkOut": int(mark_out_frame),
            "sceneMarkOutState": mark_out_state == "set",
            "sceneStartFrame": int(execute_george("tv_startframe")),
            "sceneBgColor": self._get_bg_color()
        }
        self.log.debug(
            "Scene data: {}".format(json.dumps(scene_data, indent=4))
        )
        context.data.update(scene_data)

    def _get_bg_color(self):
        """Background color set on scene.

        Is important for review exporting where scene bg color is used as
        background.
        """
        output_file = tempfile.NamedTemporaryFile(
            mode="w", prefix="a_tvp_", suffix=".txt", delete=False
        )
        output_file.close()
        output_filepath = output_file.name.replace("\\", "/")
        george_script_lines = [
            # Variable containing full path to output file
            "output_path = \"{}\"".format(output_filepath),
            "tv_background",
            "bg_color = result",
            # Write data to output file
            (
                "tv_writetextfile"
                " \"strict\" \"append\" '\"'output_path'\"' bg_color"
            )
        ]

        george_script = "\n".join(george_script_lines)
        execute_george_through_file(george_script)

        with open(output_filepath, "r") as stream:
            data = stream.read()

        os.remove(output_filepath)
        data = data.strip()
        if not data:
            return None
        return data.split(" ")
