import pyblish.api


class ValidateSopOutputNode(pyblish.api.InstancePlugin):
    """Validate the instance SOP Output Node.

    This will ensure:
        - The SOP Path is set.
        - The SOP Path refers to an existing object.
        - The SOP Path node is a SOP node.
        - The SOP Path node has at least one input connection (has an input)
        - The SOP Path has geometry data.

    """

    order = pyblish.api.ValidatorOrder
    families = ["pointcache"]
    hosts = ["houdini"]
    label = "Validate Output Node"

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                "Output node(s) `%s` are incorrect. "
                "See plug-in log for details." % invalid
            )

    @classmethod
    def get_invalid(cls, instance):

        import hou

        output_node = instance.data["output_node"]

        if output_node is None:
            node = instance[0]
            cls.log.error(
                "SOP Output node in '%s' does not exist. "
                "Ensure a valid SOP output path is set." % node.path()
            )

            return [node.path()]

        # Output node must be a Sop node.
        if not isinstance(output_node, hou.SopNode):
            cls.log.error(
                "Output node %s is not a SOP node. "
                "SOP Path must point to a SOP node, "
                "instead found category type: %s"
                % (output_node.path(), output_node.type().category().name())
            )
            return [output_node.path()]

        # For the sake of completeness also assert the category type
        # is Sop to avoid potential edge case scenarios even though
        # the isinstance check above should be stricter than this category
        assert output_node.type().category().name() == "Sop", (
            "Output node %s is not of category Sop. This is a bug.."
            % output_node.path()
        )

        # Ensure the node is cooked and succeeds to cook so we can correctly
        # check for its geometry data.
        if output_node.needsToCook():
            cls.log.debug("Cooking node: %s" % output_node.path())
            try:
                output_node.cook()
            except hou.Error as exc:
                cls.log.error("Cook failed: %s" % exc)
                cls.log.error(output_node.errors()[0])
                return [output_node.path()]

        # Ensure the output node has at least Geometry data
        if not output_node.geometry():
            cls.log.error(
                "Output node `%s` has no geometry data." % output_node.path()
            )
            return [output_node.path()]
