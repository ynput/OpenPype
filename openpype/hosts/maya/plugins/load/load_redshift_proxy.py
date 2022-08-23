# -*- coding: utf-8 -*-
"""Loader for Redshift proxy."""
import os
import clique

import maya.cmds as cmds

from openpype.api import get_project_settings
from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.hosts.maya.api.lib import (
    namespaced,
    maintained_selection,
    unique_namespace
)
from openpype.hosts.maya.api.pipeline import containerise


class RedshiftProxyLoader(load.LoaderPlugin):
    """Load Redshift proxy"""

    families = ["redshiftproxy"]
    representations = ["rs"]

    label = "Import Redshift Proxy"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, options=None):
        """Plugin entry point."""
        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "redshiftproxy"

        asset_name = context['asset']["name"]
        namespace = namespace or unique_namespace(
            asset_name + "_",
            prefix="_" if asset_name[0].isdigit() else "",
            suffix="_",
        )

        # Ensure Redshift for Maya is loaded.
        cmds.loadPlugin("redshift4maya", quiet=True)

        with maintained_selection():
            cmds.namespace(addNamespace=namespace)
            with namespaced(namespace, new=False):
                nodes, group_node = self.create_rs_proxy(
                    name, self.fname)

        self[:] = nodes
        if not nodes:
            return

        # colour the group node
        settings = get_project_settings(os.environ['AVALON_PROJECT'])
        colors = settings['maya']['load']['colors']
        c = colors.get(family)
        if c is not None:
            cmds.setAttr("{0}.useOutlinerColor".format(group_node), 1)
            cmds.setAttr("{0}.outlinerColor".format(group_node),
                         c[0], c[1], c[2])

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def update(self, container, representation):

        node = container['objectName']
        assert cmds.objExists(node), "Missing container"

        members = cmds.sets(node, query=True) or []
        rs_meshes = cmds.ls(members, type="RedshiftProxyMesh")
        assert rs_meshes, "Cannot find RedshiftProxyMesh in container"

        filename = get_representation_path(representation)

        for rs_mesh in rs_meshes:
            cmds.setAttr("{}.fileName".format(rs_mesh),
                         filename,
                         type="string")

        # Update metadata
        cmds.setAttr("{}.representation".format(node),
                     str(representation["_id"]),
                     type="string")

    def remove(self, container):

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

    def switch(self, container, representation):
        self.update(container, representation)

    def create_rs_proxy(self, name, path):
        """Creates Redshift Proxies showing a proxy object.

        Args:
            name (str): Proxy name.
            path (str): Path to proxy file.

        Returns:
            (str, str): Name of mesh with Redshift proxy and its parent
                transform.

        """
        rs_mesh = cmds.createNode(
            'RedshiftProxyMesh', name="{}_RS".format(name))
        mesh_shape = cmds.createNode("mesh", name="{}_GEOShape".format(name))

        cmds.setAttr("{}.fileName".format(rs_mesh),
                     path,
                     type="string")

        cmds.connectAttr("{}.outMesh".format(rs_mesh),
                         "{}.inMesh".format(mesh_shape))

        group_node = cmds.group(empty=True, name="{}_GRP".format(name))
        mesh_transform = cmds.listRelatives(mesh_shape,
                                            parent=True, fullPath=True)
        cmds.parent(mesh_transform, group_node)
        nodes = [rs_mesh, mesh_shape, group_node]

        # determine if we need to enable animation support
        files_in_folder = os.listdir(os.path.dirname(path))
        collections, remainder = clique.assemble(files_in_folder)

        if collections:
            cmds.setAttr("{}.useFrameExtension".format(rs_mesh), 1)

        return nodes, group_node
