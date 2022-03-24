# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.mel as mel

from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.hosts.maya.api.lib import (
    maintained_selection,
    namespaced,
    unique_namespace
)
from openpype.hosts.maya.api.pipeline import containerise


class MultiverseUsdLoader(load.LoaderPlugin):
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
        # type: (dict, dict) -> None
        """Update container with specified representation."""
        node = container['objectName']
        assert cmds.objExists(node), "Missing container"

        members = cmds.sets(node, query=True) or []
        shapes = cmds.ls(members, type="mvUsdCompoundShape")
        assert shapes, "Cannot find mvUsdCompoundShape in container"

        path = get_representation_path(representation)

        import multiverse
        for shape in shapes:
            multiverse.SetUsdCompoundAssetPaths(shape, [path])

        cmds.setAttr("{}.representation".format(node),
                     str(representation["_id"]),
                     type="string")

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        # type: (dict) -> None
        """Remove loaded container."""
        # Delete container and its contents
        if cmds.objExists(container['objectName']):
            members = cmds.sets(container['objectName'], query=True) or []
            cmds.delete([container['objectName']] + members)

        # Remove the namespace, if empty
        namespace = container['namespace']
        if cmds.namespace(exists=namespace):
            members = cmds.namespaceInfo(namespace, listNamespace=True)
            if not members:
                cmds.namespace(removeNamespace=namespace)
            else:
                self.log.warning("Namespace not deleted because it "
                                 "still has members: %s", namespace)
