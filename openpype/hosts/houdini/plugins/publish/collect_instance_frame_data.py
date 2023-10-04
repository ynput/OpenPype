import hou

import pyblish.api
from openpype.hosts.houdini.api import lib

class CollectInstanceNodeFrameRange(pyblish.api.InstancePlugin):
    """Collect time range frame data for the instance node."""

    order = pyblish.api.CollectorOrder + 0.001
    label = "Instance Node Frame Range"
    hosts = ["houdini"]

    def process(self, instance):

        node_path = instance.data.get("instance_node")
        node = hou.node(node_path) if node_path else None
        if not node_path or not node:
            self.log.debug(
                "No instance node found for instance: {}".format(instance)
            )
            return

        asset_data = instance.context.data["assetEntity"]["data"]
        frame_data = lib.get_frame_data(node, asset_data, self.log)

        if not frame_data:
            return

        self.log.info("Collected time data: {}".format(frame_data))
        instance.data.update(frame_data)
