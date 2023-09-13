# -*- coding: utf-8 -*-
import contextlib

import pyblish.api
import hou

from openpype.pipeline import PublishXmlValidationError
from openpype.hosts.houdini.api.action import SelectInvalidAction


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


@contextlib.contextmanager
def update_mode_context(mode):
    original = hou.updateModeSetting()
    try:
        hou.setUpdateMode(mode)
        yield
    finally:
        hou.setUpdateMode(original)


def get_geometry_at_frame(sop_node, frame, force=True):
    """Return geometry at frame but force a cooked value."""
    if not hasattr(sop_node, "geometry"):
        return
    with update_mode_context(hou.updateMode.AutoUpdate):
        sop_node.cook(force=force, frame_range=(frame, frame))
        return sop_node.geometryAtFrame(frame)


class ValidateVDBOutputNode(pyblish.api.InstancePlugin):
    """Validate that the node connected to the output node is of type VDB.

    All primitives of the output geometry must be VDBs, no other primitive
    types are allowed. That means that regardless of the amount of VDBs in the
    geometry it will have an equal amount of VDBs, points, primitives and
    vertices since each VDB primitive is one point, one vertex and one VDB.

    This validation only checks the geometry on the first frame of the export
    frame range for optimization purposes.

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
    actions = [SelectInvalidAction]

    def process(self, instance):
        invalid_nodes, message = self.get_invalid_with_message(instance)
        if invalid_nodes:

            # instance_node is str, but output_node is hou.Node so we convert
            output = instance.data.get("output_node")
            output_path = output.path() if output else None

            raise PublishXmlValidationError(
                self,
                "Invalid VDB content: {}".format(message),
                formatting_data={
                    "message": message,
                    "rop_path": instance.data["transientData"]["instance_node"].path(),
                    "sop_path": output_path
                }
            )

    @classmethod
    def get_invalid_with_message(cls, instance):

        node = instance.data.get("output_node")
        if node is None:
            instance_node = instance.data.get("instance_node")
            error = (
                "SOP path is not correctly set on "
                "ROP node `{}`.".format(instance_node.path())
            )
            return [instance_node, error]

        frame = instance.data.get("frameStart", 0)
        geometry = get_geometry_at_frame(node, frame)
        if geometry is None:
            # No geometry data on this node, maybe the node hasn't cooked?
            error = (
                "SOP node `{}` has no geometry data. "
                "Was it unable to cook?".format(node.path())
            )
            return [node, error]

        num_prims = geometry.intrinsicValue("primitivecount")
        num_points = geometry.intrinsicValue("pointcount")
        if num_prims == 0 and num_points == 0:
            # Since we are only checking the first frame it doesn't mean there
            # won't be VDB prims in a few frames. As such we'll assume for now
            # the user knows what he or she is doing
            cls.log.warning(
                "SOP node `{}` has no primitives on start frame {}. "
                "Validation is skipped and it is assumed elsewhere in the "
                "frame range VDB prims and only VDB prims will exist."
                "".format(node.path(), int(frame))
            )
            return [None, None]

        num_vdb_prims = geometry.countPrimType(hou.primType.VDB)
        cls.log.debug("Detected {} VDB primitives".format(num_vdb_prims))
        if num_prims != num_vdb_prims:
            # There's at least one primitive that is not a VDB.
            # Search them and report them to the artist.
            prims = geometry.prims()
            invalid_prims = [prim for prim in prims
                             if not isinstance(prim, hou.VDB)]
            if invalid_prims:
                # Log prim numbers as consecutive ranges so logging isn't very
                # slow for large number of primitives
                error = (
                    "Found non-VDB primitives for `{}`. "
                    "Primitive indices {} are not VDB primitives.".format(
                        node.path(),
                        ", ".join(group_consecutive_numbers(
                            prim.number() for prim in invalid_prims
                        ))
                    )
                )
                return [node, error]

        if num_points != num_vdb_prims:
            # We have points unrelated to the VDB primitives.
            error = (
                "The number of primitives and points do not match in '{}'. "
                "This likely means you have unconnected points, which we do "
                "not allow in the VDB output.".format(node.path()))
            return [node, error]

        return [None, None]

    @classmethod
    def get_invalid(cls, instance):
        nodes, _ = cls.get_invalid_with_message(instance)
        return nodes
