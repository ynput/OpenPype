# -*- coding: utf-8 -*-
"""Loader for image sequences."""
import os
import uuid

import clique

from avalon import api, harmony
import pype.lib


class ImageSequenceLoader(api.Loader):
    """Load image sequences.

    Stores the imported asset in a container named after the asset.
    """

    families = ["shot", "render", "image", "plate", "reference"]
    representations = ["jpeg", "png", "jpg"]

    def load(self, context, name=None, namespace=None, data=None):
        """Plugin entry point.

        Args:
            context (:class:`pyblish.api.Context`): Context.
            name (str, optional): Container name.
            namespace (str, optional): Container namespace.
            data (dict, optional): Additional data passed into loader.

        """
        self_name = self.__class__.__name__
        collections, remainder = clique.assemble(
            os.listdir(os.path.dirname(self.fname))
        )
        files = []
        if collections:
            for f in list(collections[0]):
                files.append(
                    os.path.join(
                        os.path.dirname(self.fname), f
                    ).replace("\\", "/")
                )
        else:
            files.append(
                os.path.join(
                    os.path.dirname(self.fname), remainder[0]
                ).replace("\\", "/")
            )

        name = context["subset"]["name"]
        name += "_{}".format(uuid.uuid4())
        read_node = harmony.send(
            {
                "function": f"PypeHarmony.Loaders.{self_name}.importFiles",  # noqa: E501
                "args": ["Top", files, name, 1]
            }
        )["result"]

        return harmony.containerise(
            name,
            namespace,
            read_node,
            context,
            self_name,
            nodes=[read_node]
        )

    def update(self, container, representation):
        """Update loaded containers.

        Args:
            container (dict): Container data.
            representation (dict): Representation data.

        """
        self_name = self.__class__.__name__
        node = harmony.find_node_by_name(container["name"], "READ")

        path = api.get_representation_path(representation)
        collections, remainder = clique.assemble(
            os.listdir(os.path.dirname(path))
        )
        files = []
        if collections:
            for f in list(collections[0]):
                files.append(
                    os.path.join(
                        os.path.dirname(path), f
                    ).replace("\\", "/")
                )
        else:
            files.append(
                os.path.join(
                    os.path.dirname(path), remainder[0]
                ).replace("\\", "/")
            )

        harmony.send(
            {
                "function": f"PypeHarmony.Loaders.{self_name}.replaceFiles",
                "args": [files, node, 1]
            }
        )

        # Colour node.
        if pype.lib.is_latest(representation):
            harmony.send(
                {
                    "function": "PypeHarmony.setColor",
                    "args": [node, [0, 255, 0, 255]]
                })
        else:
            harmony.send(
                {
                    "function": "PypeHarmony.setColor",
                    "args": [node, [255, 0, 0, 255]]
                })

        harmony.imprint(
            node, {"representation": str(representation["_id"])}
        )

    def remove(self, container):
        """Remove loaded container.

        Args:
            container (dict): Container data.

        """
        node = harmony.find_node_by_name(container["name"], "READ")
        harmony.send(
            {"function": "PypeHarmony.deleteNode", "args": [node]}
        )
        harmony.imprint(node, {}, remove=True)

    def switch(self, container, representation):
        """Switch loaded representations."""
        self.update(container, representation)
