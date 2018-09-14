import hou

import pyblish.api

from avalon.houdini import lib


class CollectInstances(pyblish.api.ContextPlugin):
    """Gather instances by all node in out graph and pre-defined attributes

    This collector takes into account assets that are associated with
    an specific node and marked with a unique identifier;

    Identifier:
        id (str): "pyblish.avalon.instance

    Specific node:
        The specific node is important because it dictates in which way the subset
        is being exported.

        alembic: will export Alembic file which supports cascading attributes
                 like 'cbId' and 'path'
        geometry: Can export a wide range of file types, default out

    """

    order = pyblish.api.CollectorOrder - 0.01
    label = "Collect Instances"
    hosts = ["houdini"]

    def process(self, context):

        instances = []

        nodes = hou.node("/out").children()
        for node in nodes:

            if not node.parm("id"):
                continue

            if node.parm("id").eval() != "pyblish.avalon.instance":
                continue

            has_family = node.parm("family").eval()
            assert has_family, "'%s' is missing 'family'" % node.name()

            data = lib.read(node)

            # temporarily translation of `active` to `publish` till issue has
            # been resolved, https://github.com/pyblish/pyblish-base/issues/307
            if "active" in data:
                data["publish"] = data["active"]

            data.update(self.get_frame_data(node))

            # Create nice name
            # All nodes in the Outputs graph have the 'Valid Frame Range'
            # attribute, we check here if any frames are set
            label = data.get("name", node.name())
            if "startFrame" in data:
                frames = "[{startFrame} - {endFrame}]".format(**data)
                label = "{} {}".format(label, frames)

            instance = context.create_instance(label)

            instance[:] = [node]
            instance.data.update(data)

            instances.append(instance)

        def sort_by_family(instance):
            """Sort by family"""
            return instance.data.get("families", instance.data.get("family"))

        # Sort/grouped by family (preserving local index)
        context[:] = sorted(context, key=sort_by_family)

        return context

    def get_frame_data(self, node):
        """Get the frame data: start frame, end frame and steps
        Args:
            node(hou.Node)

        Returns:
            dict

        """

        data = {}

        if node.parm("trange") is None:
            return data

        if node.parm("trange").eval() == 0:
            return data

        data["startFrame"] = node.parm("f1").eval()
        data["endFrame"] = node.parm("f2").eval()
        data["steps"] = node.parm("f3").eval()

        return data
