import pyblish.api
import pype.api


class ValidateAnimationContent(pyblish.api.InstancePlugin):
    """Adheres to the content of 'animation' family

    - Must have collected `out_hierarchy` data.
    - All nodes in `out_hierarchy` must be in the instance.

    """

    order = pype.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["animation"]
    label = "Animation Content"
    actions = [pype.api.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):
        assert 'out_hierarchy' in instance.data, "Missing `out_hierarchy` data"

        # All nodes in the `out_hierarchy` must be among the nodes that are
        # in the instance. The nodes in the instance are found from the top
        # group, as such this tests whether all nodes are under that top group.

        lookup = set(instance[:])
        invalid = [node for node in instance.data['out_hierarchy'] if
                   node not in lookup]

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Animation content is invalid. See log.")
