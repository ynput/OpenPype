# -*- coding: utf-8 -*-
"""Loader for image sequences."""
import os
import uuid
from pathlib import Path

import clique

from avalon import api
import openpype.hosts.harmony.api as harmony
import openpype.lib


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
        fname = Path(self.fname)
        self_name = self.__class__.__name__
        collections, remainder = clique.assemble(
            os.listdir(fname.parent.as_posix())
        )
        files = []
        if collections:
            for f in list(collections[0]):
                files.append(fname.parent.joinpath(f).as_posix())
        else:
            files.append(fname.parent.joinpath(remainder[0]).as_posix())

        asset = context["asset"]["name"]
        subset = context["subset"]["name"]

        group_id = str(uuid.uuid4())
        read_node = harmony.send(
            {
                "function": f"PypeHarmony.Loaders.{self_name}.importFiles",  # noqa: E501
                "args": [
                    files,
                    asset,
                    subset,
                    1,
                    group_id
                ]
            }
        )["result"]

        return harmony.containerise(
            f"{asset}_{subset}",
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
        node = container.get("nodes").pop()

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
        if openpype.lib.is_latest(representation):
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
        node = container.get("nodes").pop()
        harmony.send(
            {"function": "PypeHarmony.deleteNode", "args": [node]}
        )
        harmony.imprint(node, {}, remove=True)

    def switch(self, container, representation):
        """Switch loaded representations."""
        self.update(container, representation)
