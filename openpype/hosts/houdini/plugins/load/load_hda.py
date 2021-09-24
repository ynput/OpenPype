# -*- coding: utf-8 -*-
from avalon import api

from avalon.houdini import pipeline, lib


class HdaLoader(api.Loader):
    """Load Houdini Digital Asset file."""

    families = ["hda"]
    label = "Load Hda"
    representations = ["hda"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        import os
        import hou

        # Format file name, Houdini only wants forward slashes
        file_path = os.path.normpath(self.fname)
        file_path = file_path.replace("\\", "/")

        # Get the root node
        obj = hou.node("/obj")

        # Create a unique name
        counter = 1
        namespace = namespace or context["asset"]["name"]
        formatted = "{}_{}".format(namespace, name) if namespace else name
        node_name = "{0}_{1:03d}".format(formatted, counter)

        hou.hda.installFile(file_path)
        print("installing {}".format(name))
        hda_node = obj.createNode(name, node_name)

        self[:] = [hda_node]

        return pipeline.containerise(
            node_name,
            namespace,
            [hda_node],
            context,
            self.__class__.__name__,
            suffix="",
        )

    def update(self, container, representation):
        hda_node = container["node"]
        hda_def = hda_node.type().definition()


    def remove(self, container):
        pass
