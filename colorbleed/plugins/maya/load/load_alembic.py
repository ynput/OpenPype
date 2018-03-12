import colorbleed.maya.plugin


class AbcLoader(colorbleed.maya.plugin.ReferenceLoader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["colorbleed.animation",
                "colorbleed.pointcache"]
    label = "Reference animation"
    representations = ["abc"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds

        cmds.loadPlugin("AbcImport.mll", quiet=True)
        nodes = cmds.file(self.fname,
                          namespace=namespace,
                          sharedReferenceFile=False,
                          groupReference=True,
                          groupName="{}:{}".format(namespace, name),
                          reference=True,
                          returnNewNodes=True)

        self[:] = nodes

        return nodes

    def switch(self, container, representation):
        self.update(container, representation)
