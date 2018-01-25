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

        # Check the Maya version, lockTransform has been introduced since
        # Maya 2017
        version = int(cmds.about(version=True))
        if version >= 2017:
            for camera in cameras:
                cmds.camera(camera, edit=True, lockTransform=True)
        else:
            self.log.warning("This version of Maya does not support locking of"
                             " transforms of cameras.")

        self[:] = nodes

        return nodes
