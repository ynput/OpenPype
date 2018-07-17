import hou

import pyblish.api

from avalon.houdini import lib


class CollectInstances(pyblish.api.ContextPlugin):

    label = "Collect Instances"
    order = pyblish.api.CollectorOrder
    hosts = ["houdini"]

    def process(self, context):

        instances = []

        nodes = hou.node("/out").children()
        for node in nodes:
            if node.parm("id"):
                continue

            if not node.parm("id") != "pyblish.avalon.instance":
                continue

            has_family = node.parm("family")
            assert has_family, "'%s' is missing 'family'" % node.name()

            # TODO: Ensure not all data passes through!
            data = lib.read(node)
            instance = context.create_instance(data.get("name", node.name()))
            instance[:] = [node]


