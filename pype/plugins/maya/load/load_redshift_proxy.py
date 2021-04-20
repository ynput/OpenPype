# -*- coding: utf-8 -*-
"""Loader for Redshift proxy."""
import os
from avalon.maya import lib
from avalon import api
from pype.api import config

import maya.cmds as cmds
import clique


class RedshiftProxyLoader(api.Loader):
    """Load Redshift proxy"""

    families = ["redshiftproxy"]
    representations = ["rs"]

    label = "Import Redshift Proxy"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, options=None):
        """Plugin entry point."""

        from avalon.maya.pipeline import containerise
        from pype.hosts.maya.lib import namespaced

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "redshiftproxy"

        asset_name = context['asset']["name"]
        namespace = namespace or lib.unique_namespace(
            asset_name + "_",
            prefix="_" if asset_name[0].isdigit() else "",
            suffix="_",
        )

        # Ensure Redshift for Maya is loaded.
        cmds.loadPlugin("redshift4maya", quiet=True)

        with lib.maintained_selection():
            cmds.namespace(addNamespace=namespace)
            with namespaced(namespace, new=False):
                nodes, group_node = self.create_rs_proxy(
                    name, self.fname)

        self[:] = nodes
        if not nodes:
            return

        # colour the group node
        presets = config.get_presets(project=os.environ['AVALON_PROJECT'])
        colors = presets['plugins']['maya']['load']['colors']
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

        filename = api.get_representation_path(representation)

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
        # Create a new shader RedshiftMaterial shader
        rs_shader = cmds.shadingNode('RedshiftMaterial', asShader=True)
        cmds.setAttr(
            "{}.diffuse_color".format(rs_shader),
            0.35, 0.35, 0.35, type='double3')
        # Create shading group for it
        rs_shading_group = cmds.sets(
            renderable=True, noSurfaceShader=True, empty=True, name='rsSG')
        cmds.connectAttr("{}.outColor".format(rs_shader),
                         "{}.surfaceShader".format(rs_shading_group),
                         force=True)

        # add path to proxy
        cmds.setAttr("{}.fileName".format(rs_mesh),
                     path,
                     type="string")

        # connect nodes
        cmds.connectAttr("{}.outMesh".format(rs_mesh),
                         "{}.inMesh".format(mesh_shape))

        # put proxy under group node
        group_node = cmds.group(empty=True, name="{}_GRP".format(name))
        mesh_transform = cmds.listRelatives(mesh_shape,
                                            parent=True, fullPath=True)
        cmds.parent(mesh_transform, group_node)
        nodes = [rs_mesh, mesh_shape, group_node]

        # determine if we need to enable animation support
        files_in_folder = os.listdir(os.path.dirname(path))
        collections, _ = clique.assemble(files_in_folder)

        # set Preview Mesh on proxy
        if collections:
            cmds.setAttr("{}.useFrameExtension".format(rs_mesh), 1)

        cmds.setAttr("{}.displayMode".format(rs_mesh), 1)
        cmds.refresh()

        # add mesh to new shading group
        cmds.sets([mesh_shape], addElement=rs_shading_group)

        return nodes, group_node
