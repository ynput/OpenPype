from avalon.maya import lib
import colorbleed.maya.plugin

import maya.cmds as cmds


class VRayProxyLoader(colorbleed.maya.plugin.ReferenceLoader):
    """Load vrmesh files"""

    families = ["colorbleed.vrayproxy"]
    representations = ["vrmesh"]

    label = "Reference VRay Proxy"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        asset_name = context['asset']["name"]
        print("---", namespace)

        namespace = namespace or lib.unique_namespace(
            asset_name + "_",
            prefix="_" if asset_name[0].isdigit() else "",
            suffix="_",
        )

        print(">>>", namespace)

        # Pre-run check
        if not cmds.objExists("vraySettings"):
            cmds.createNode("VRaySettingsNode", name="vraySettings")

        # Add namespace
        cmds.namespace(set=":")
        cmds.namespace(add=namespace)
        cmds.namespace(set=namespace)

        with lib.maintained_selection():
            nodes = self.create_vray_proxy(name)

        self[:] = nodes
        # Make sure to restore the default namespace, or anything imported or
        # refereced after this gets added to this namespace
        cmds.namespace(set=":")

        return nodes

    def create_vray_proxy(self, name, attrs=None):
        """Re-create the structure created by VRay to support vrmeshes

        Args:
            name(str): name of the asset

        Returns:
            nodes(list)
        """

        # Create nodes
        vray_mesh = cmds.createNode('VRayMesh', name="{}_VRMS".format(name))
        mesh_shape = cmds.createNode("mesh", name="{}_GEOShape".format(name))
        vray_mat = cmds.createNode("VRayMeshMaterial",
                                   name="{}_VRMM".format(name))
        vray_mat_sg = cmds.createNode("shadingEngine",
                                      name="{}_VRSG".format(name))

        cmds.setAttr("{}.fileName2".format(vray_mesh),
                     self.fname,
                     type="string")

        # Apply attributes from export
        # cmds.setAttr("{}.animType".format(vray_mesh), 3)

        # Create important connections
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

        return nodes
