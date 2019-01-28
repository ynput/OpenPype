import pype.maya.plugin


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

        # Ensure FBX plug-in is loaded
        cmds.loadPlugin("fbxmaya", quiet=True)

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
