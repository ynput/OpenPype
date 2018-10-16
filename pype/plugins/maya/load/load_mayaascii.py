import pype.maya.plugin


class MayaAsciiLoader(pype.maya.plugin.ReferenceLoader):
    """Load the model"""

    families = ["studio.mayaAscii"]
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
