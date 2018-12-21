import pyblish.api


class ValidateOutputNode(pyblish.api.InstancePlugin):
    """Validate the instance SOP Output Node.

    This will ensure:
        - The SOP Path is set.
        - The SOP Path refers to an existing object.
        - The SOP Path node is of type 'output' or 'camera'
        - The SOP Path node has at least one input connection (has an input)

    """

    order = pyblish.api.ValidatorOrder
    families = ["colorbleed.pointcache",
                "colorbleed.vdbcache"]
    hosts = ["houdini"]
    label = "Validate Output Node"

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Output node(s) `%s` are incorrect. "
                               "See plug-in log for details." % invalid)

    @classmethod
    def get_invalid(cls, instance):

        output_node = instance.data["output_node"]

        if output_node is None:
            node = instance[0]
            cls.log.error("SOP Output node in '%s' does not exist. "
                          "Ensure a valid SOP output path is set."
                          % node.path())

            return node.path()

        # Check if type is correct
        type_name = output_node.type().name()
        if type_name != "output":
            cls.log.error("Output node `%s` is not an `output` type node."
                          % output_node.path())
            return [output_node.path()]

        # Check if output node has incoming connections
        if type_name == "output" and not output_node.inputConnections():
            cls.log.error("Output node `%s` has no incoming connections"
                          % output_node.path())
            return [output_node.path()]
