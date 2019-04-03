import pype.maya.plugin
import os
import json


class YetiRigLoader(pype.maya.plugin.ReferenceLoader):

    families = ["yetiRig"]
    representations = ["ma"]

    label = "Load Yeti Rig"
    order = -9
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name=None, namespace=None, data=None):

        import maya.cmds as cmds
        from avalon import maya

        with maya.maintained_selection():
            nodes = cmds.file(self.fname,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName="{}:{}".format(namespace, name))

        groupName = "{}:{}".format(namespace, name)
        preset_file = os.path.join(
            os.environ.get('PYPE_STUDIO_TEMPLATES'),
            'presets', 'tools',
            'family_colors.json'
        )
        with open(preset_file, 'r') as cfile:
            colors = json.load(cfile)

        c = colors.get('yetiRig')
        if c is not None:
            cmds.setAttr(groupName + ".useOutlinerColor", 1)
            cmds.setAttr(groupName + ".outlinerColor",
                         c[0], c[1], c[2])
        self[:] = nodes

        self.log.info("Yeti Rig Connection Manager will be available soon")

        return nodes
