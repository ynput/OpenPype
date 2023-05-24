# -*- coding: utf-8 -*-
"""Collector plugin for frames data on ROP instances."""
import hou  # noqa
import pyblish.api
from openpype.hosts.houdini.api import lib


class CollectRopFrameRange(pyblish.api.InstancePlugin):
    """Collect all frames which would be saved from the ROP nodes"""

    order = pyblish.api.CollectorOrder
    label = "Collect RopNode Frame Range"

    def process(self, instance):

        node_path = instance.data.get("instance_node")
        if node_path is None:
            # Instance without instance node like a workfile instance
            return

        ropnode = hou.node(node_path)
        frame_data = lib.get_frame_data(ropnode)

        if "frameStart" in frame_data and "frameEnd" in frame_data:

            # Log artist friendly message about the collected frame range
            message = (
                "Frame range {0[frameStart]} - {0[frameEnd]}"
            ).format(frame_data)
            if frame_data.get("step", 1.0) != 1.0:
                message += " with step {0[step]}".format(frame_data)
            self.log.info(message)

            instance.data.update(frame_data)

            # Add frame range to label if the instance has a frame range.
            label = instance.data.get("label", instance.data["name"])
            instance.data["label"] = (
                "{0} [{1[frameStart]} - {1[frameEnd]}]".format(label,
                                                               frame_data)
            )
