import colorbleed.maya.plugin


class CameraLoader(colorbleed.maya.plugin.ReferenceLoader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["colorbleed.camera"]
    label = "Reference camera"
    representations = ["abc"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds
        # import pprint
        # Get family type from the context

        cmds.loadPlugin("AbcImport.mll", quiet=True)
        nodes = cmds.file(self.fname,
                          namespace=namespace,
                          sharedReferenceFile=False,
                          groupReference=True,
                          groupName="{}:{}".format(namespace, name),
                          reference=True,
                          returnNewNodes=True)

        cameras = cmds.ls(nodes, type="camera")
        for camera in cameras:
            cmds.camera(camera, edit=True, lockTransform=True)

        self[:] = nodes

        return nodes
