import pyblish.api
import openpype.api
from openpype.pipeline import PublishXmlValidationError
import hou


class ValidateVDBOutputNode(pyblish.api.InstancePlugin):
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
    label = "Validate Output Node (VDB)"

    def process(self, instance):

        data = {
            "node": instance
        }

        output_node = instance.data["output_node"]
        if output_node is None:
            raise PublishXmlValidationError(
                self,
                "SOP Output node in '{node}' does not exist. Ensure a valid "
                "SOP output path is set.".format(**data),
                key="noSOP",
                formatting_data=data
            )

        # Output node must be a Sop node.
        if not isinstance(output_node, hou.SopNode):
            data = {
                "nodepath": output_node.path(),
                "categoryname": output_node.type().category().name()
            }
            raise PublishXmlValidationError(
                self,
                "Output node {nodepath} is not a SOP node. SOP Path must"
                "point to a SOP node, instead found category"
                "type: {categoryname}".format(**data),
                key="wrongSOP",
                formatting_data=data
            )

        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishXmlValidationError(
                self,
                "Output node(s) `{}` are incorrect. See plug-in"
                "log for details.".format(invalid),
                formatting_data=data
            )

    @classmethod
    def get_invalid(cls, instance):

        output_node = instance.data["output_node"]

        frame = instance.data.get("frameStart", 0)
        geometry = output_node.geometryAtFrame(frame)
        if geometry is None:
            # No geometry data on this output_node
            #   - maybe the node hasn't cooked?
            cls.log.debug(
                "SOP node has no geometry data. "
                "Is it cooked? %s" % output_node.path()
            )
            return [output_node]

        prims = geometry.prims()
        nr_of_prims = len(prims)

        # All primitives must be hou.VDB
        invalid_prim = False
        for prim in prims:
            if not isinstance(prim, hou.VDB):
                cls.log.debug("Found non-VDB primitive: %s" % prim)
                invalid_prim = True
        if invalid_prim:
            return [instance]

        nr_of_points = len(geometry.points())
        if nr_of_points != nr_of_prims:
            cls.log.debug("The number of primitives and points do not match")
            return [instance]

        for prim in prims:
            if prim.numVertices() != 1:
                cls.log.debug("Found primitive with more than 1 vertex!")
                return [instance]
