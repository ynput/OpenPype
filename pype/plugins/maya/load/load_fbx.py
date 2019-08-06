import pype.maya.plugin
import os
from pypeapp import config


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

        presets = config.get_presets(project=os.environ['AVALON_PROJECT'])
        colors = presets['plugins']['maya']['load']['colors']

        c = colors.get(family)
        if c is not None:
            cmds.setAttr(groupName + ".useOutlinerColor", 1)
            cmds.setAttr(groupName + ".outlinerColor",
                         c[0], c[1], c[2])

        self[:] = nodes

        return nodes

    def switch(self, container, representation):
        self.update(container, representation)
