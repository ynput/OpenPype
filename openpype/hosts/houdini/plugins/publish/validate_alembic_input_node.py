import pyblish.api
import openpype.api


class ValidateAlembicInputNode(pyblish.api.InstancePlugin):
    """Validate that the node connected to the output is correct

    The connected node cannot be of the following types for Alembic:
        - VDB
        - Volume

    """

    order = openpype.api.ValidateContentsOrder + 0.1
    families = ["pointcache"]
    hosts = ["houdini"]
    label = "Validate Input Node (Abc)"

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Node connected to the output node incorrect")

    @classmethod
    def get_invalid(cls, instance):

        invalid_nodes = ["VDB", "Volume"]
        node = instance.data["output_node"]

        prims = node.geometry().prims()

        for prim in prims:
            prim_type = prim.type().name()
            if prim_type in invalid_nodes:
                cls.log.error("Found a primitive which is of type '%s' !"
                              % prim_type)
                return [instance]
