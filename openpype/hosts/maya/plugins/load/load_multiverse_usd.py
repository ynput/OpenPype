# -*- coding: utf-8 -*-
from avalon import api

import maya.cmds as cmds


class MultiverseUsdLoader(api.Loader):
    """Load the USD by Multiverse"""

    families = ["usd"]
    representations = ["usd", "usda", "usdc", "usdz", "abc"]

    label = "Read USD by Multiverse"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, options=None):

        from openpype.hosts.maya.api.pipeline import containerise
        from openpype.hosts.maya.api.lib import unique_namespace

        asset = context['asset']['name']
        namespace = namespace or unique_namespace(
            asset + "_",
            prefix="_" if asset[0].isdigit() else "",
            suffix="_",
        )

        cmds.loadPlugin("MultiverseForMaya", quiet=True)

        # Root group
        label = "{}:{}".format(namespace, name)
        root = cmds.group(name=label, empty=True)

        # Create shape and move it under root
        import multiverse
        shape = multiverse.CreateUsdCompound(self.fname)
        cmds.parent(shape, root)

    def update(self, container, representation):

        path = api.get_representation_path(representation)

        # Update the shape
        members = cmds.sets(container['objectName'], query=True)
        shapes = cmds.ls(members, type="mvUsdPackedShape", long=True)

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
