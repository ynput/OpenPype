import pyblish.api


class ValidateOutputNode(pyblish.api.InstancePlugin):
    """Validate if output node:
        - exists
        - is of type 'output'
        - has an input"""

    order = pyblish.api.ValidatorOrder
    families = ["*"]
    hosts = ["houdini"]
    label = "Validate Output Node"

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Output node(s) `%s` are incorrect" % invalid)

    @classmethod
    def get_invalid(cls, instance):

        output_node = instance.data["output_node"]

        if output_node is None:
            node = instance[0]
            cls.log.error("Output node at '%s' does not exist, see source" %
                          node.path())

            return node.path()

        # Check if type is correct
        type_name = output_node.type().name()
        if type_name not in ["output", "cam"]:
            cls.log.error("Output node `%s` is not an accepted type `output` "
                          "or `camera`" %
                          output_node.path())
            return [output_node.path()]

        # Check if output node has incoming connections
        if type_name == "output" and not output_node.inputConnections():
            cls.log.error("Output node `%s` has no incoming connections"
                          % output_node.path())
            return [output_node.path()]
