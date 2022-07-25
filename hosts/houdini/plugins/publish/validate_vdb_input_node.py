import pyblish.api
import openpype.api


class ValidateVDBInputNode(pyblish.api.InstancePlugin):
    """Validate that the node connected to the output node is of type VDB.

    Regardless of the amount of VDBs create the output will need to have an
    equal amount of VDBs, points, primitives and vertices

    A VDB is an inherited type of Prim, holds the following data:
        - Primitives: 1
        - Points: 1
        - Vertices: 1
        - VDBs: 1

    """

    order = openpype.api.ValidateContentsOrder + 0.1
    families = ["vdbcache"]
    hosts = ["houdini"]
    label = "Validate Input Node (VDB)"

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError(
                "Node connected to the output node is not" "of type VDB!"
            )

    @classmethod
    def get_invalid(cls, instance):

        node = instance.data["output_node"]

        prims = node.geometry().prims()
        nr_of_prims = len(prims)

        nr_of_points = len(node.geometry().points())
        if nr_of_points != nr_of_prims:
            cls.log.error("The number of primitives and points do not match")
            return [instance]

        for prim in prims:
            if prim.numVertices() != 1:
                cls.log.error("Found primitive with more than 1 vertex!")
                return [instance]
