from openpype.pipeline import LegacyCreator
import openpype.hosts.harmony.api as harmony


class Creator(LegacyCreator):
    """Creator plugin to create instances in Harmony.

    By default a Composite node is created to support any number of nodes in
    an instance, but any node type is supported.
    If the selection is used, the selected nodes will be connected to the
    created node.
    """

    defaults = ["Main"]
    node_type = "COMPOSITE"

    def setup_node(self, node):
        """Prepare node as container.

        Args:
            node (str): Path to node.
        """
        harmony.send(
            {
                "function": "AvalonHarmony.setupNodeForCreator",
                "args": node
            }
        )

    def process(self):
        """Plugin entry point."""
        existing_node_names = harmony.send(
            {
                "function": "AvalonHarmony.getNodesNamesByType",
                "args": self.node_type
            })["result"]

        # Dont allow instances with the same name.
        msg = "Instance with name \"{}\" already exists.".format(self.name)
        for name in existing_node_names:
            if self.name.lower() == name.lower():
                harmony.send(
                    {
                        "function": "AvalonHarmony.message", "args": msg
                    }
                )
                return False

        with harmony.maintained_selection() as selection:
            node = None

            if (self.options or {}).get("useSelection") and selection:
                node = harmony.send(
                    {
                        "function": "AvalonHarmony.createContainer",
                        "args": [self.name, self.node_type, selection[-1]]
                    }
                )["result"]
            else:
                node = harmony.send(
                    {
                        "function": "AvalonHarmony.createContainer",
                        "args": [self.name, self.node_type]
                    }
                )["result"]

            harmony.imprint(node, self.data)
            self.setup_node(node)

        return node
