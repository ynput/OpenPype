import config.apps.maya.plugin


class YetiRigLoader(config.apps.maya.plugin.ReferenceLoader):

    families = ["studio.yetiRig"]
    representations = ["ma"]

    label = "Load Yeti Rig"
    order = -9
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name=None, namespace=None, data=None):

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

        self.log.info("Yeti Rig Connection Manager will be available soon")

        return nodes
