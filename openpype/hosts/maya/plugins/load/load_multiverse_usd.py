# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.mel as mel

from avalon import api

from openpype.hosts.maya.api.lib import (
    maintained_selection,
    namespaced,
    unique_namespace
)
from openpype.hosts.maya.api.pipeline import containerise


class MultiverseUsdLoader(api.Loader):
    """Load the USD by Multiverse"""

    families = ["model", "usd", "usdComposition", "usdOverride"]
    representations = ["usd", "usda", "usdc", "usdz", "abc"]

    label = "Read USD by Multiverse"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, options=None):

        asset = context['asset']['name']
        namespace = namespace or unique_namespace(
            asset + "_",
            prefix="_" if asset[0].isdigit() else "",
            suffix="_",
        )

        # Create the shape
        cmds.loadPlugin("MultiverseForMaya", quiet=True)

        shape = None
        transform = None
        with maintained_selection():
            cmds.namespace(addNamespace=namespace)
            with namespaced(namespace, new=False):
                import multiverse
                shape = multiverse.CreateUsdCompound(self.fname)
                transform = mel.eval('firstParentOf "{}"'.format(shape))

        nodes = [transform, shape]
        self[:] = nodes

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def update(self, container, representation):

        path = api.get_representation_path(representation)

        # Update the shape
        members = cmds.sets(container['objectName'], query=True)
        shapes = cmds.ls(members, type="mvUsdCompoundShape", long=True)

        assert len(shapes) == 1, "This is a bug"

        import multiverse
        for shape in shapes:
            multiverse.SetUsdCompoundAssetPaths(shape, [path])

        cmds.setAttr(container["objectName"] + ".representation",
                     str(representation["_id"]),
                     type="string")

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        pass
