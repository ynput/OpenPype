import pype.maya.plugin
import os
import json


class FBXLoader(pype.maya.plugin.ReferenceLoader):
    """Load the FBX"""

    families = ["fbx"]
    representations = ["fbx"]

    label = "Reference FBX"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds
        from avalon import maya

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "fbx"

        # Ensure FBX plug-in is loaded
        cmds.loadPlugin("fbxmaya", quiet=True)

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

        c = colors.get(family)
        if c is not None:
            cmds.setAttr(groupName + ".useOutlinerColor", 1)
            cmds.setAttr(groupName + ".outlinerColor",
                         c[0], c[1], c[2])

        self[:] = nodes

        return nodes

    def switch(self, container, representation):
        self.update(container, representation)
