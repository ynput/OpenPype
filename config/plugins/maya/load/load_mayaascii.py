import config.maya.plugin


class MayaAsciiLoader(config.maya.plugin.ReferenceLoader):
    """Load the model"""

    families = ["config.mayaAscii"]
    representations = ["ma"]

    label = "Reference Maya Ascii"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds
        from avalon import maya

        with maya.maintained_selection():
            nodes = cmds.file(self.fname,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName="{}:{}".format(namespace, name))

        self[:] = nodes

        return nodes

    def switch(self, container, representation):
        self.update(container, representation)
