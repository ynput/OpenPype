# -*- coding: utf-8 -*-
"""Collector plugin for frames data on ROP instances."""
import hou  # noqa
import pyblish.api
from openpype.hosts.houdini.api import lib


class CollectRopFrameRange(pyblish.api.InstancePlugin):
    """Collect all frames which would be saved from the ROP nodes"""

    hosts = ["houdini"]
    order = pyblish.api.CollectorOrder
    label = "Collect RopNode Frame Range"

    def process(self, instance):

        node_path = instance.data.get("instance_node")
        if node_path is None:
            # Instance without instance node like a workfile instance
            self.log.debug(
                "No instance node found for instance: {}".format(instance)
            )
            return

        ropnode = hou.node(node_path)
        frame_data = lib.get_frame_data(
            ropnode, self.log
        )

        if not frame_data:
            return

        # Log debug message about the collected frame range
        self.log.debug(
            "Collected frame_data: {}".format(frame_data)
        )

        instance.data.update(frame_data)
