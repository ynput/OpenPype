import pype.maya.plugin
import os
import json


class CameraLoader(pype.maya.plugin.ReferenceLoader):
    """Specific loader of Alembic for the pype.camera family"""

    families = ["camera"]
    label = "Reference camera"
    representations = ["abc", "ma"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds
        # Get family type from the context

        cmds.loadPlugin("AbcImport.mll", quiet=True)
        groupName = "{}:{}".format(namespace, name)
        nodes = cmds.file(self.fname,
                          namespace=namespace,
                          sharedReferenceFile=False,
                          groupReference=True,
                          groupName="{}:{}".format(namespace, name),
                          reference=True,
                          returnNewNodes=True)

        cameras = cmds.ls(nodes, type="camera")

        preset_file = os.path.join(
            os.environ.get('PYPE_STUDIO_TEMPLATES'),
            'presets', 'tools',
            'family_colors.json'
        )
        with open(preset_file, 'r') as cfile:
            colors = json.load(cfile)

        c = colors.get('camera')
        if c is not None:
            cmds.setAttr(groupName + ".useOutlinerColor", 1)
            cmds.setAttr(groupName + ".outlinerColor",
                         c[0], c[1], c[2])

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

    def switch(self, container, representation):
        self.update(container, representation)
