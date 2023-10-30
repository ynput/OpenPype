from openpype.pipeline import load


class LOPLoadAssetLoader(load.LoaderPlugin):

    families = ["*"]
    label = "Load Asset (LOPs)"
    representations = ["usd", "abc", "usda", "usdc"]
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        import toolutils
        kwargs = {}
        node = toolutils.genericTool(kwargs, "ayon::lop_import",
                                     exact_node_type=False)
        if not node:
            return

        # Define node name
        namespace = namespace if namespace else context["asset"]["name"]
        node_name = "{}_{}".format(namespace, name) if namespace else name
        node.setName(node_name, unique_name=True)

        # Set representation id
        representation_id = str(context["representation"]["_id"])
        parm = node.parm("representation")
        parm.set(representation_id)
        parm.pressButton()  # trigger callbacks

        nodes = [node]
        self[:] = nodes

    def update(self, container, representation):
        node = container["node"]

        representation_id = str(representation["_id"])
        parm = node.parm("representation")
        parm.set(representation_id)
        parm.pressButton()  # trigger callbacks

    def remove(self, container):
        node = container["node"]
        node.destroy()

    def switch(self, container, representation):
        self.update(container, representation)
