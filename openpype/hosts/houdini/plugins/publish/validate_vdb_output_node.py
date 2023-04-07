# -*- coding: utf-8 -*-
import pyblish.api
import hou
from openpype.pipeline import PublishXmlValidationError


def group_consecutive_numbers(nums):
    """
    Args:
        nums (list): List of sorted integer numbers.

    Yields:
        str: Group ranges as {start}-{end} if more than one number in the range
            else it yields {end}

    """
    start = None
    end = None

    def _result(a, b):
        if a == b:
            return "{}".format(a)
        else:
            return "{}-{}".format(a, b)

    for num in nums:
        if start is None:
            start = num
            end = num
        elif num == end + 1:
            end = num
        else:
            yield _result(start, end)
            start = num
            end = num
    if start is not None:
        yield _result(start, end)


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

    order = pyblish.api.ValidatorOrder + 0.1
    families = ["vdbcache"]
    hosts = ["houdini"]
    label = "Validate Output Node (VDB)"

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishXmlValidationError(
                self,
                "Node connected to the output node is not of type VDB."
            )

    @classmethod
    def get_invalid(cls, instance):

        node = instance.data.get("output_node")
        if node is None:
            cls.log.error(
                "SOP path is not correctly set on "
                "ROP node '%s'." % instance.data.get("instance_node")
            )
            return [instance]

        frame = instance.data.get("frameStart", 0)
        geometry = node.geometryAtFrame(frame)
        if geometry is None:
            # No geometry data on this node, maybe the node hasn't cooked?
            cls.log.error(
                "SOP node has no geometry data. "
                "Is it cooked? %s" % node.path()
            )
            return [node]

        prims = geometry.prims()
        nr_of_prims = len(prims)

        # All primitives must be hou.VDB
        invalid_prims = []
        for prim in prims:
            if not isinstance(prim, hou.VDB):
                invalid_prims.append(prim)
        if invalid_prims:
            # Log prim numbers as consecutive ranges so logging isn't very
            # slow for large number of primitives
            cls.log.error(
                "Found non-VDB primitives for '{}', "
                "primitive indices: {}".format(
                    node.path(),
                    ", ".join(group_consecutive_numbers(
                        prim.number() for prim in invalid_prims
                    ))
                )
            )
            return [instance]

        nr_of_points = len(geometry.points())
        if nr_of_points != nr_of_prims:
            cls.log.error("The number of primitives and points do not match")
            return [instance]

        for prim in prims:
            if prim.numVertices() != 1:
                cls.log.error("Found primitive with more than 1 vertex!")
                return [instance]
