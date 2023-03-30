import openpype.hosts.maya.api.plugin
from openpype.hosts.maya.api.lib import get_container_members


class CameraLoader(openpype.hosts.maya.api.plugin.ReferenceLoader):
    """Reference Camera"""

    families = ["camera", "camerarig"]
    label = "Reference camera"
    representations = ["abc", "ma"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds
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
        # Maya 2016.5 Ext 2
        version = int(cmds.about(version=True))
        if version >= 2016:
            for camera in cameras:
                cmds.camera(camera, edit=True, lockTransform=True)
        else:
            self.log.warning("This version of Maya does not support locking of"
                             " transforms of cameras.")

        self[:] = nodes

        return nodes

    def update(self, container, representation):

        from maya import cmds

        # Get the modelPanels that used the old camera
        members = get_container_members(container)
        old_cameras = cmds.ls(members, type="camera", long=True)
        update_panels = []
        for panel in cmds.getPanel(type="modelPanel"):
            cam = cmds.ls(cmds.modelPanel(panel, query=True, camera=True),
                          long=True)

            # Often but not always maya returns the transform from the
            # modelPanel as opposed to the camera shape, so we convert it
            # to explicitly be the camera shape
            if cmds.nodeType(cam) != "camera":
                cam = cmds.listRelatives(cam,
                                         children=True,
                                         fullPath=True,
                                         type="camera")[0]
            if cam in old_cameras:
                update_panels.append(panel)

        # Perform regular reference update
        super(CameraLoader, self).update(container, representation)

        # Update the modelPanels to contain the new camera
        members = get_container_members(container)
        new_cameras = cmds.ls(members, type="camera", long=True)
        new_camera = new_cameras[0]
        for panel in update_panels:
            cmds.modelPanel(panel, edit=True, camera=new_camera)
