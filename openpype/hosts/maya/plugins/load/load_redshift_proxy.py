# -*- coding: utf-8 -*-
"""Loader for Redshift proxy."""
from avalon.maya import lib
from avalon import api
from openpype.api import get_project_settings
import os
import maya.cmds as cmds


class RedshiftProxyLoader(api.Loader):
    """Load Redshift proxy"""

    families = ["redshiftproxy"]
    representations = ["vrmesh"]

    label = "Import Redshift Proxy"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, options=None):
        """Plugin entry point."""

        from avalon.maya.pipeline import containerise
        from openpype.hosts.maya.api.lib import namespaced

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
                nodes, group_node = self.create_redshift_proxy(name,
                                               filename=self.fname)

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
            node
        """
        import pymel.core as pm

        proxy_mesh_node = pm.createNode('RedshiftProxyMesh')
        proxy_mesh_node.fileName.set(path)
        proxy_mesh_shape = pm.createNode('mesh', n=name)
        proxy_mesh_node.outMesh >> proxy_mesh_shape.inMesh

        # assign default material
        pm.sets('initialShadingGroup', fe=proxy_mesh_shape)

        return proxy_mesh_node, proxy_mesh_shape