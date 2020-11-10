import json

import pyblish.api
from avalon.tvpaint import pipeline, lib


class CollectWorkfileData(pyblish.api.ContextPlugin):
    label = "Collect Workfile Data"
    order = pyblish.api.CollectorOrder - 1.01
    hosts = ["tvpaint"]

    def process(self, context):
        self.log.info("Collecting instance data from workfile")
        instance_data = pipeline.list_instances()
        self.log.debug(
            "Instance data:\"{}".format(json.dumps(instance_data, indent=4))
        )
        context.data["workfileInstances"] = instance_data

        self.log.info("Collecting layers data from workfile")
        layers_data = lib.layers_data()
        self.log.debug(
            "Layers data:\"{}".format(json.dumps(layers_data, indent=4))
        )
        context.data["layersData"] = layers_data

        self.log.info("Collecting groups data from workfile")
        group_data = lib.groups_data()
        self.log.debug(
            "Group data:\"{}".format(json.dumps(group_data, indent=4))
        )
        context.data["groupsData"] = group_data

        self.log.info("Collecting scene data from workfile")
        workfile_info_parts = lib.execute_george("tv_projectinfo").split(" ")

        frame_start = int(workfile_info_parts.pop(-1))
        field_order = workfile_info_parts.pop(-1)
        frame_rate = float(workfile_info_parts.pop(-1))
        pixel_apsect = float(workfile_info_parts.pop(-1))
        height = int(workfile_info_parts.pop(-1))
        width = int(workfile_info_parts.pop(-1))
        workfile_path = " ".join(workfile_info_parts).replace("\"", "")

        sceme_data = {
            "currentFile": workfile_path,
            "sceneWidth": width,
            "sceneHeight": height,
            "pixelAspect": pixel_apsect,
            "frameStart": frame_start,
            "fps": frame_rate,
            "fieldOrder": field_order
        }
        self.log.debug(
            "Scene data: {}".format(json.dumps(sceme_data, indent=4))
        )
        context.data.update(sceme_data)
