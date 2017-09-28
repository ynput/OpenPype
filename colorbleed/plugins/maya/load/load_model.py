from avalon import api


class ModelLoader(api.Loader):
    """Load the model"""

    families = ["colorbleed.model"]
    representations = ["ma"]

    label = "Reference Model"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process(self, name, namespace, context, data):

        import maya.cmds as cmds
        from avalon import maya

        # Create a readable namespace
        # Namespace should contain asset name and counter
        # TEST_001{_descriptor} where `descriptor` can be `_abc` for example
        assetname = "{}_".format(namespace.split("_")[0])
        namespace = maya.unique_namespace(assetname, format="%03d")

        with maya.maintained_selection():
            nodes = cmds.file(self.fname,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName="{}:{}".format(namespace, name))

        self[:] = nodes