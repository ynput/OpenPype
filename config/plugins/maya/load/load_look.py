import config.apps.maya.plugin


class LookLoader(config.apps.maya.plugin.ReferenceLoader):
    """Specific loader for lookdev"""

    families = ["colorbleed.look"]
    representations = ["ma"]

    label = "Reference look"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):
        """
        Load and try to ssign Lookdev to nodes based on relationship data
        Args:
            name:
            namespace:
            context:
            data:

        Returns:

        """

        import maya.cmds as cmds
        from avalon import maya

        with maya.maintained_selection():
            nodes = cmds.file(self.fname,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True)

        self[:] = nodes

    def switch(self, container, representation):
        self.update(container, representation)
