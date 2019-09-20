import pype.maya.plugin
from pypeapp import config
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

        presets = config.get_presets(project=os.environ['AVALON_PROJECT'])
        colors = presets['plugins']['maya']['load']['colors']

        c = colors.get(family)
        if c is not None:
            cmds.setAttr(groupName + ".useOutlinerColor", 1)
            cmds.setAttr(groupName + ".outlinerColor",
                         c[0], c[1], c[2])
            cmds.setAttr(groupName + ".displayHandle", 1)
            # get bounding box
            bbox = cmds.exactWorldBoundingBox(groupName)
            # get pivot position on world space
            pivot = cmds.xform(groupName, q=True, sp=True, ws=True)
            # center of bounding box
            cx = (bbox[0] + bbox[3]) / 2
            cy = (bbox[1] + bbox[4]) / 2
            cz = (bbox[2] + bbox[5]) / 2
            # add pivot position to calculate offset
            cx = cx + pivot[0]
            cy = cy + pivot[1]
            cz = cz + pivot[2]
            # set selection handle offset to center of bounding box
            cmds.setAttr(groupName + ".selectHandleX", cx)
            cmds.setAttr(groupName + ".selectHandleY", cy)
            cmds.setAttr(groupName + ".selectHandleZ", cz)
        return nodes

    def switch(self, container, representation):
        self.update(container, representation)
