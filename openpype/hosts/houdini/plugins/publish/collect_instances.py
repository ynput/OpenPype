import hou

import pyblish.api

from openpype.hosts.houdini.api import lib


class CollectInstances(pyblish.api.ContextPlugin):
    """Gather instances by all node in out graph and pre-defined attributes

    This collector takes into account assets that are associated with
    an specific node and marked with a unique identifier;

    Identifier:
        id (str): "pyblish.avalon.instance

    Specific node:
        The specific node is important because it dictates in which way the
        subset is being exported.

        alembic: will export Alembic file which supports cascading attributes
                 like 'cbId' and 'path'
        geometry: Can export a wide range of file types, default out

    """

    order = pyblish.api.CollectorOrder - 0.01
    label = "Collect Instances"
    hosts = ["houdini"]

    def process(self, context):

        nodes = hou.node("/out").children()
        nodes += hou.node("/obj").children()

        # Include instances in USD stage only when it exists so it
        # remains backwards compatible with version before houdini 18
        stage = hou.node("/stage")
        if stage:
            nodes += stage.recursiveGlob("*", filter=hou.nodeTypeFilter.Rop)

        for node in nodes:

            if not node.parm("id"):
                continue

            if node.evalParm("id") != "pyblish.avalon.instance":
                continue

            has_family = node.evalParm("family")
            assert has_family, "'%s' is missing 'family'" % node.name()

            self.log.info("processing {}".format(node))

            data = lib.read(node)
            # Check bypass state and reverse
            if hasattr(node, "isBypassed"):
                data.update({"active": not node.isBypassed()})

            # temporarily translation of `active` to `publish` till issue has
            # been resolved, https://github.com/pyblish/pyblish-base/issues/307
            if "active" in data:
                data["publish"] = data["active"]

            data.update(self.get_frame_data(node))

            # Create nice name if the instance has a frame range.
            label = data.get("name", node.name())
            label += " (%s)" % data["asset"]  # include asset in name

            if "frameStart" in data and "frameEnd" in data:
                frames = "[{frameStart} - {frameEnd}]".format(**data)
                label = "{} {}".format(label, frames)

            instance = context.create_instance(label)

            # Include `families` using `family` data
            instance.data["families"] = [instance.data["family"]]

            instance[:] = [node]
            instance.data.update(data)

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

        if node.evalParm("trange") == 0:
            return data

        data["frameStart"] = node.evalParm("f1")
        data["frameEnd"] = node.evalParm("f2")
        data["steps"] = node.evalParm("f3")

        return data
