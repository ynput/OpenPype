import hou

import pyblish.api


class CollectInstanceNodeFrameRange(pyblish.api.InstancePlugin):
    """Collect time range frame data for the instance node."""

    order = pyblish.api.CollectorOrder + 0.001
    label = "Instance Node Frame Range"
    hosts = ["houdini"]

    def process(self, instance):

        node_path = instance.data.get("instance_node")
        node = hou.node(node_path) if node_path else None
        if not node_path or not node:
            self.log.debug("No instance node found for instance: "
                           "{}".format(instance))
            return

        frame_data = self.get_frame_data(node)
        if not frame_data:
            return

        self.log.info("Collected time data: {}".format(frame_data))
        instance.data.update(frame_data)

    def get_frame_data(self, node):
        """Get the frame data: start frame, end frame and steps
        Args:
            node(hou.Node)

        Returns:
            dict

        """

        data = {}

        if node.parm("trange") is None:
            self.log.debug("Node has no 'trange' parameter: "
                           "{}".format(node.path()))
            return data

        if node.evalParm("trange") == 0:
            # Ignore 'render current frame'
            self.log.debug("Node '{}' has 'Render current frame' set. "
                           "Time range data ignored.".format(node.path()))
            return data

        data["frameStart"] = node.evalParm("f1")
        data["frameEnd"] = node.evalParm("f2")
        data["byFrameStep"] = node.evalParm("f3")

        return data
