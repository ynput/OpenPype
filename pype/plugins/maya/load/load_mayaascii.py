import pype.maya.plugin
import json
import os


class MayaAsciiLoader(pype.maya.plugin.ReferenceLoader):
    """Load the model"""

    families = ["mayaAscii",
                "setdress",
                "layout"]
    representations = ["ma"]

    label = "Reference Maya Ascii"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds
        from avalon import maya

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "model"

        with maya.maintained_selection():
            nodes = cmds.file(self.fname,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName="{}:{}".format(namespace, name))

        self[:] = nodes
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

        return nodes

    def switch(self, container, representation):
        self.update(container, representation)
