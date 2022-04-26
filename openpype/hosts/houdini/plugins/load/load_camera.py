from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.houdini.api import pipeline


ARCHIVE_EXPRESSION = ('__import__("_alembic_hom_extensions")'
                      '.alembicGetCameraDict')


def transfer_non_default_values(src, dest, ignore=None):
    """Copy parm from src to dest.

    Because the Alembic Archive rebuilds the entire node
    hierarchy on triggering "Build Hierarchy" we want to
    preserve any local tweaks made by the user on the camera
    for ease of use. That could be a background image, a
    resolution change or even Redshift camera parameters.

    We try to do so by finding all Parms that exist on both
    source and destination node, include only those that both
    are not at their default value, they must be visible,
    we exclude those that have the special "alembic archive"
    channel expression and ignore certain Parm types.

    """
    import hou

    src.updateParmStates()

    for parm in src.allParms():

        if ignore and parm.name() in ignore:
            continue

        # If destination parm does not exist, ignore..
        dest_parm = dest.parm(parm.name())
        if not dest_parm:
            continue

        # Ignore values that are currently at default
        if parm.isAtDefault() and dest_parm.isAtDefault():
            continue

        if not parm.isVisible():
            # Ignore hidden parameters, assume they
            # are implementation details
            continue

        expression = None
        try:
            expression = parm.expression()
        except hou.OperationFailed:
            # No expression present
            pass

        if expression is not None and ARCHIVE_EXPRESSION in expression:
            # Assume it's part of the automated connections that the
            # Alembic Archive makes on loading of the camera and thus we do
            # not want to transfer the expression
            continue

        # Ignore folders, separators, etc.
        ignore_types = {
            hou.parmTemplateType.Toggle,
            hou.parmTemplateType.Menu,
            hou.parmTemplateType.Button,
            hou.parmTemplateType.FolderSet,
            hou.parmTemplateType.Separator,
            hou.parmTemplateType.Label,
        }
        if parm.parmTemplate().type() in ignore_types:
            continue

        print("Preserving attribute: %s" % parm.name())
        dest_parm.setFromParm(parm)


class CameraLoader(load.LoaderPlugin):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["camera"]
    label = "Load Camera (abc)"
    representations = ["abc"]
    order = -10

    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        import os
        import hou

        # Format file name, Houdini only wants forward slashes
        file_path = os.path.normpath(self.fname)
        file_path = file_path.replace("\\", "/")

        # Get the root node
        obj = hou.node("/obj")

        # Define node name
        namespace = namespace if namespace else context["asset"]["name"]
        node_name = "{}_{}".format(namespace, name) if namespace else name

        # Create a archive node
        container = self.create_and_connect(obj, "alembicarchive", node_name)

        # TODO: add FPS of project / asset
        container.setParms({"fileName": file_path,
                            "channelRef": True})

        # Apply some magic
        container.parm("buildHierarchy").pressButton()
        container.moveToGoodPosition()

        # Create an alembic xform node
        nodes = [container]

        self[:] = nodes

        return pipeline.containerise(node_name,
                                     namespace,
                                     nodes,
                                     context,
                                     self.__class__.__name__,
                                     suffix="")

    def update(self, container, representation):

        node = container["node"]

        # Update the file path
        file_path = get_representation_path(representation)
        file_path = file_path.replace("\\", "/")

        # Update attributes
        node.setParms({"fileName": file_path,
                       "representation": str(representation["_id"])})

        # Store the cam temporarily next to the Alembic Archive
        # so that we can preserve parm values the user set on it
        # after build hierarchy was triggered.
        old_camera = self._get_camera(node)
        temp_camera = old_camera.copyTo(node.parent())

        # Rebuild
        node.parm("buildHierarchy").pressButton()

        # Apply values to the new camera
        new_camera = self._get_camera(node)
        transfer_non_default_values(temp_camera,
                                    new_camera,
                                    # The hidden uniform scale attribute
                                    # gets a default connection to
                                    # "icon_scale" just skip that completely
                                    ignore={"scale"})

        temp_camera.destroy()

    def remove(self, container):

        node = container["node"]
        node.destroy()

    def _get_camera(self, node):
        import hou
        cameras = node.recursiveGlob("*",
                                     filter=hou.nodeTypeFilter.ObjCamera,
                                     include_subnets=False)

        assert len(cameras) == 1, "Camera instance must have only one camera"
        return cameras[0]

    def create_and_connect(self, node, node_type, name=None):
        """Create a node within a node which and connect it to the input

        Args:
            node(hou.Node): parent of the new node
            node_type(str) name of the type of node, eg: 'alembic'
            name(str, Optional): name of the node

        Returns:
            hou.Node

        """
        if name:
            new_node = node.createNode(node_type, node_name=name)
        else:
            new_node = node.createNode(node_type)

        new_node.moveToGoodPosition()
        return new_node
