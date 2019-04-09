import pype.maya.plugin
import os
from pypeapp import config


class AbcLoader(pype.maya.plugin.ReferenceLoader):
    """Specific loader of Alembic for the pype.animation family"""

    families = ["animation",
                "pointcache"]
    label = "Reference animation"
    representations = ["abc"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "animation"

        groupName = "{}:{}".format(namespace, name)
        cmds.loadPlugin("AbcImport.mll", quiet=True)
        nodes = cmds.file(self.fname,
                          namespace=namespace,
                          sharedReferenceFile=False,
                          groupReference=True,
                          groupName="{}:{}".format(namespace, name),
                          reference=True,
                          returnNewNodes=True)

        cmds.makeIdentity(groupName, apply=False, rotate=True,
                          translate=True, scale=True)

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
