from avalon.maya import lib
from avalon import api
from pype.api import config
import os
import maya.cmds as cmds


class VRayProxyLoader(api.Loader):
    """Load VRayMesh proxy"""

    families = ["vrayproxy"]
    representations = ["vrmesh"]

    label = "Import VRay Proxy"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):

        from avalon.maya.pipeline import containerise
        from pype.hosts.maya.lib import namespaced

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "vrayproxy"

        asset_name = context['asset']["name"]
        namespace = namespace or lib.unique_namespace(
            asset_name + "_",
            prefix="_" if asset_name[0].isdigit() else "",
            suffix="_",
        )

        # Ensure V-Ray for Maya is loaded.
        cmds.loadPlugin("vrayformaya", quiet=True)

        with lib.maintained_selection():
            cmds.namespace(addNamespace=namespace)
            with namespaced(namespace, new=False):
                nodes = self.create_vray_proxy(name,
                                               filename=self.fname)

        self[:] = nodes
        if not nodes:
            return

        presets = config.get_presets(project=os.environ['AVALON_PROJECT'])
        colors = presets['plugins']['maya']['load']['colors']

        c = colors.get(family)
        if c is not None:
            cmds.setAttr("{0}_{1}.useOutlinerColor".format(name, "GRP"), 1)
            cmds.setAttr("{0}_{1}.outlinerColor".format(name, "GRP"),
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
        vraymeshes = cmds.ls(members, type="VRayMesh")
        assert vraymeshes, "Cannot find VRayMesh in container"

        filename = api.get_representation_path(representation)

        for vray_mesh in vraymeshes:
            cmds.setAttr("{}.fileName".format(vray_mesh),
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

    def create_vray_proxy(self, name, filename):
        """Re-create the structure created by VRay to support vrmeshes

        Args:
            name(str): name of the asset

        Returns:
            nodes(list)
        """

        # Create nodes
        vray_mesh = cmds.createNode('VRayMesh', name="{}_VRMS".format(name))
        mesh_shape = cmds.createNode("mesh", name="{}_GEOShape".format(name))
        vray_mat = cmds.shadingNode("VRayMeshMaterial", asShader=True,
                                    name="{}_VRMM".format(name))
        vray_mat_sg = cmds.sets(name="{}_VRSG".format(name),
                                empty=True,
                                renderable=True,
                                noSurfaceShader=True)

        cmds.setAttr("{}.fileName".format(vray_mesh),
                     filename,
                     type="string")

        # Create important connections
        cmds.connectAttr("time1.outTime",
                         "{0}.currentFrame".format(vray_mesh))
        cmds.connectAttr("{}.fileName2".format(vray_mesh),
                         "{}.fileName".format(vray_mat))
        cmds.connectAttr("{}.instancing".format(vray_mesh),
                         "{}.instancing".format(vray_mat))
        cmds.connectAttr("{}.output".format(vray_mesh),
                         "{}.inMesh".format(mesh_shape))
        cmds.connectAttr("{}.overrideFileName".format(vray_mesh),
                         "{}.overrideFileName".format(vray_mat))
        cmds.connectAttr("{}.currentFrame".format(vray_mesh),
                         "{}.currentFrame".format(vray_mat))

        # Set surface shader input
        cmds.connectAttr("{}.outColor".format(vray_mat),
                         "{}.surfaceShader".format(vray_mat_sg))

        # Connect mesh to shader
        cmds.sets([mesh_shape], addElement=vray_mat_sg)

        group_node = cmds.group(empty=True, name="{}_GRP".format(name))
        mesh_transform = cmds.listRelatives(mesh_shape,
                                            parent=True, fullPath=True)
        cmds.parent(mesh_transform, group_node)
        nodes = [vray_mesh, mesh_shape, vray_mat, vray_mat_sg, group_node]

        # Fix: Force refresh so the mesh shows correctly after creation
        cmds.refresh()
        cmds.setAttr("{}.geomType".format(vray_mesh), 2)

        return nodes
