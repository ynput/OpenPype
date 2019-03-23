import pype.maya.plugin
import os
import json


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

        preset_file = os.path.join(
            os.environ.get('PYPE_STUDIO_TEMPLATES'),
            'presets', 'tools',
            'family_colors.json'
        )
        with open(preset_file, 'r') as cfile:
            colors = json.load(cfile)

        c = colors.get('pointcache')
        if c is not None:
            cmds.setAttr(groupName + ".useOutlinerColor", 1)
            cmds.setAttr(groupName + ".outlinerColor",
                         c[0], c[1], c[2])

        self[:] = nodes

        return nodes

    def switch(self, container, representation):
        self.update(container, representation)
