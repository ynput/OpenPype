# -*- coding: utf-8 -*-
"""Loader for Vray Proxy files.

If there are Alembics published along vray proxy (in the same version),
loader will use them instead of native vray vrmesh format.

"""
import os

import maya.cmds as cmds

from avalon import io
from openpype.api import get_project_settings
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


class VRayProxyLoader(load.LoaderPlugin):
    """Load VRay Proxy with Alembic or VrayMesh."""

    families = ["vrayproxy", "model", "pointcache", "animation"]
    representations = ["vrmesh", "abc"]

    label = "Import VRay Proxy"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, options=None):
        # type: (dict, str, str, dict) -> None
        """Loader entry point.

        Args:
            context (dict): Loaded representation context.
            name (str): Name of container.
            namespace (str): Optional namespace name.
            options (dict): Optional loader options.

        """

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "vrayproxy"

        #  get all representations for this version
        self.fname = self._get_abc(context["version"]["_id"]) or self.fname

        asset_name = context['asset']["name"]
        namespace = namespace or unique_namespace(
            asset_name + "_",
            prefix="_" if asset_name[0].isdigit() else "",
            suffix="_",
        )

        # Ensure V-Ray for Maya is loaded.
        cmds.loadPlugin("vrayformaya", quiet=True)

        with maintained_selection():
            cmds.namespace(addNamespace=namespace)
            with namespaced(namespace, new=False):
                nodes, group_node = self.create_vray_proxy(
                    name, filename=self.fname)

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
                (float(c[0])/255),
                (float(c[1])/255),
                (float(c[2])/255)
            )

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
        vraymeshes = cmds.ls(members, type="VRayMesh")
        assert vraymeshes, "Cannot find VRayMesh in container"

        #  get all representations for this version
        filename = (
            self._get_abc(representation["parent"])
            or get_representation_path(representation)
        )

        for vray_mesh in vraymeshes:
            cmds.setAttr("{}.fileName".format(vray_mesh),
                         filename,
                         type="string")

        # Update metadata
        cmds.setAttr("{}.representation".format(node),
                     str(representation["_id"]),
                     type="string")

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

    def switch(self, container, representation):
        # type: (dict, dict) -> None
        """Switch loaded representation."""
        self.update(container, representation)

    def create_vray_proxy(self, name, filename):
        # type: (str, str) -> (list, str)
        """Re-create the structure created by VRay to support vrmeshes

        Args:
            name (str): Name of the asset.
            filename (str): File name of vrmesh.

        Returns:
            nodes(list)

        """

        if name is None:
            name = os.path.splitext(os.path.basename(filename))[0]

        parent = cmds.createNode("transform", name=name)
        proxy = cmds.createNode(
            "VRayProxy", name="{}Shape".format(name), parent=parent)
        cmds.setAttr(proxy + ".fileName", filename, type="string")
        cmds.connectAttr("time1.outTime", proxy + ".currentFrame")

        return [parent, proxy], parent

    def _get_abc(self, version_id):
        # type: (str) -> str
        """Get abc representation file path if present.

        If here is published Alembic (abc) representation published along
        vray proxy, get is file path.

        Args:
            version_id (str): Version hash id.

        Returns:
            str: Path to file.
            None: If abc not found.

        """
        self.log.debug(
            "Looking for abc in published representations of this version.")
        abc_rep = io.find_one(
            {
                "type": "representation",
                "parent": io.ObjectId(version_id),
                "name": "abc"
            })

        if abc_rep:
            self.log.debug("Found, we'll link alembic to vray proxy.")
            file_name = get_representation_path(abc_rep)
            self.log.debug("File: {}".format(self.fname))
            return file_name

        return ""
