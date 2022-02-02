from avalon.maya import lib
from avalon import api
from openpype.api import get_project_settings
import os
import maya.cmds as cmds


class VRaySceneLoader(api.Loader):
    """Load Vray scene"""

    families = ["vrayscene_layer"]
    representations = ["vrscene"]

    label = "Import VRay Scene"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):

        from avalon.maya.pipeline import containerise
        from openpype.hosts.maya.api.lib import namespaced

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "vrayscene_layer"

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
                nodes, group_node = self.create_vray_scene(name,
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

        node = container['objectName']
        assert cmds.objExists(node), "Missing container"

        members = cmds.sets(node, query=True) or []
        vraymeshes = cmds.ls(members, type="VRayScene")
        assert vraymeshes, "Cannot find VRayScene in container"

        filename = api.get_representation_path(representation)

        for vray_mesh in vraymeshes:
            cmds.setAttr("{}.FilePath".format(vray_mesh),
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

    def create_vray_scene(self, name, filename):
        """Re-create the structure created by VRay to support vrscenes

        Args:
            name(str): name of the asset

        Returns:
            nodes(list)
        """

        # Create nodes
        mesh_node_name = "VRayScene_{}".format(name)

        trans = cmds.createNode(
            "transform", name="{}".format(mesh_node_name))
        mesh = cmds.createNode(
            "mesh", name="{}_Shape".format(mesh_node_name), parent=trans)
        vray_scene = cmds.createNode(
            "VRayScene", name="{}_VRSCN".format(mesh_node_name), parent=trans)

        cmds.connectAttr(
            "{}.outMesh".format(vray_scene), "{}.inMesh".format(mesh))

        cmds.setAttr("{}.FilePath".format(vray_scene), filename, type="string")

        # Create important connections
        cmds.connectAttr("time1.outTime",
                         "{0}.inputTime".format(trans))

        # Connect mesh to initialShadingGroup
        cmds.sets([mesh], forceElement="initialShadingGroup")

        group_node = cmds.group(empty=True, name="{}_GRP".format(name))
        cmds.parent(trans, group_node)
        nodes = [trans, vray_scene, mesh, group_node]

        # Fix: Force refresh so the mesh shows correctly after creation
        cmds.refresh()

        return nodes, group_node
