# -*- coding: utf-8 -*-
import maya.cmds as cmds
from maya import mel
import os

import qargparse

from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.hosts.maya.api.lib import (
    maintained_selection
)
from openpype.hosts.maya.api.pipeline import containerise
from openpype.client import get_representation_by_id


class MultiverseUsdOverLoader(load.LoaderPlugin):
    """Reference file"""

    families = ["mvUsdOverride"]
    representations = ["usda", "usd", "udsz"]

    label = "Load Usd Override into Compound"
    order = -10
    icon = "code-fork"
    color = "orange"

    options = [
        qargparse.String(
            "Which Compound",
            label="Compound",
            help="Select which compound to add this as a layer to."
        )
    ]

    def load(self, context, name=None, namespace=None, options=None):
        current_usd = cmds.ls(selection=True,
                              type="mvUsdCompoundShape",
                              dag=True,
                              long=True)
        if len(current_usd) != 1:
            self.log.error("Current selection invalid: '{}', "
                           "must contain exactly 1 mvUsdCompoundShape."
                           "".format(current_usd))
            return

        # Make sure we can load the plugin
        cmds.loadPlugin("MultiverseForMaya", quiet=True)
        import multiverse

        path = self.filepath_from_context(context)
        nodes = current_usd
        with maintained_selection():
            multiverse.AddUsdCompoundAssetPath(current_usd[0], path)

        namespace = current_usd[0].split("|")[1].split(":")[0]

        container = containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

        cmds.addAttr(container, longName="mvUsdCompoundShape",
                     niceName="mvUsdCompoundShape", dataType="string")
        cmds.setAttr(container + ".mvUsdCompoundShape",
                     current_usd[0], type="string")

        return container

    def update(self, container, representation):
        # type: (dict, dict) -> None
        """Update container with specified representation."""

        cmds.loadPlugin("MultiverseForMaya", quiet=True)
        import multiverse

        node = container['objectName']
        assert cmds.objExists(node), "Missing container"

        members = cmds.sets(node, query=True) or []
        shapes = cmds.ls(members, type="mvUsdCompoundShape")
        assert shapes, "Cannot find mvUsdCompoundShape in container"

        mvShape = container['mvUsdCompoundShape']
        assert mvShape, "Missing mv source"

        project_name = representation["context"]["project"]["name"]
        prev_representation_id = cmds.getAttr("{}.representation".format(node))
        prev_representation = get_representation_by_id(project_name,
                                                       prev_representation_id)
        prev_path = os.path.normpath(prev_representation["data"]["path"])

        path = get_representation_path(representation)

        for shape in shapes:
            asset_paths = multiverse.GetUsdCompoundAssetPaths(shape)
            asset_paths = [os.path.normpath(p) for p in asset_paths]

            assert asset_paths.count(prev_path) == 1, \
                "Couldn't find matching path (or too many)"
            prev_path_idx = asset_paths.index(prev_path)
            asset_paths[prev_path_idx] = path
            multiverse.SetUsdCompoundAssetPaths(shape, asset_paths)

        cmds.setAttr("{}.representation".format(node),
                     str(representation["_id"]),
                     type="string")
        mel.eval('refreshEditorTemplates;')

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
