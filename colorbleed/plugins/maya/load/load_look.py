import colorbleed.maya.plugin


class LookLoader(colorbleed.maya.plugin.ReferenceLoader):
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
        import colorbleed.maya.lib as lib

        # try / except here is to ensure that the get_reference_node
        # does not fail when the file doesn't exist yet
        reference_node = None
        try:
            reference_node = lib.get_reference_node(self.fname)
        except Exception as e:
            self.log.error(e)
            pass

        if reference_node is None:
            self.log.info("Loading lookdev for the first time ...")
            with maya.maintained_selection():
                nodes = cmds.file(self.fname,
                                  namespace=namespace,
                                  reference=True,
                                  returnNewNodes=True)
        else:
            self.log.info("Reusing existing lookdev ...")
            nodes = None

        self[:] = nodes
