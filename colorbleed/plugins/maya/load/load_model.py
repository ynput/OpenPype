from maya import cmds

from avalon import api


class ModelLoader(api.Loader):
    """Load models

    Stores the imported asset in a container named after the asset.

    """

    families = ["colorbleed.model"]
    representations = ["ma"]

    def process(self, name, namespace, context):
        from avalon import maya
        with maya.maintained_selection():
            nodes = cmds.file(
                self.fname,
                namespace=namespace,
                reference=True,
                returnNewNodes=True,
                groupReference=True,
                groupName=namespace + ":" + name
            )

        # Assign default shader to meshes
        meshes = cmds.ls(nodes, type="mesh")
        cmds.sets(meshes, forceElement="initialShadingGroup")

        self[:] = nodes
