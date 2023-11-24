# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
from openpype.hosts.houdini.api.action import (
    SelectInvalidAction,
    SelectROPAction,
)
from openpype.hosts.houdini.api.lib import get_obj_node_output
import hou


class ValidateFBXOutputNode(pyblish.api.InstancePlugin):
    """Validate the instance Output Node.

    This will ensure:
        - The Output Node Path is set.
        - The Output Node Path refers to an existing object.
        - The Output Node is a Sop or Obj node.
        - The Output Node has geometry data.
        - The Output Node doesn't include invalid primitive types.
    """

    order = pyblish.api.ValidatorOrder
    families = ["fbx"]
    hosts = ["houdini"]
    label = "Validate FBX Output Node"
    actions = [SelectROPAction, SelectInvalidAction]

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            nodes = [n.path() for n in invalid]
            raise PublishValidationError(
                "See log for details. "
                "Invalid nodes: {0}".format(nodes),
                title="Invalid output node(s)"
            )

    @classmethod
    def get_invalid(cls, instance):
        output_node = instance.data.get("output_node")

        # Check if The Output Node Path is set and
        #  refers to an existing object.
        if output_node is None:
            rop_node = hou.node(instance.data["instance_node"])
            cls.log.error(
                "Output node in '%s' does not exist. "
                "Ensure a valid output path is set.", rop_node.path()
            )

            return [rop_node]

        # Check if the Output Node is a Sop or an Obj node
        #  also, list all sop output nodes inside as well as
        #  invalid empty nodes.
        all_out_sops = []
        invalid = []

        # if output_node is an ObjSubnet or an ObjNetwork
        if output_node.childTypeCategory() == hou.objNodeTypeCategory():
            for node in output_node.allSubChildren():
                if node.type().name() == "geo":
                    out = get_obj_node_output(node)
                    if out:
                        all_out_sops.append(out)
                    else:
                        invalid.append(node)  # empty_objs
                        cls.log.error(
                            "Geo Obj Node '%s' is empty!",
                            node.path()
                        )
            if not all_out_sops:
                invalid.append(output_node)  # empty_objs
                cls.log.error(
                    "Output Node '%s' is empty!",
                    node.path()
                )

        # elif output_node is an ObjNode
        elif output_node.type().name() == "geo":
            out = get_obj_node_output(output_node)
            if out:
                all_out_sops.append(out)
            else:
                invalid.append(node)  # empty_objs
                cls.log.error(
                    "Output Node '%s' is empty!",
                    node.path()
                )

        # elif output_node is a SopNode
        elif output_node.type().category().name() == "Sop":
            all_out_sops.append(output_node)

        # Then it's a wrong node type
        else:
            cls.log.error(
                "Output node %s is not a SOP or OBJ Geo or OBJ SubNet node. "
                "Instead found category type: %s %s",
                output_node.path(), output_node.type().category().name(),
                output_node.type().name()
            )
            return [output_node]

        # Check if all output sop nodes have geometry
        #  and don't contain invalid prims
        invalid_prim_types = ["VDB", "Volume"]
        for sop_node in all_out_sops:
            # Empty Geometry test
            if not hasattr(sop_node, "geometry"):
                invalid.append(sop_node)  # empty_geometry
                cls.log.error(
                    "Sop node '%s' doesn't include any prims.",
                    sop_node.path()
                )
                continue

            frame = instance.data.get("frameStart", 0)
            geo = sop_node.geometryAtFrame(frame)
            if len(geo.iterPrims()) == 0:
                invalid.append(sop_node)  # empty_geometry
                cls.log.error(
                    "Sop node '%s' doesn't include any prims.",
                    sop_node.path()
                )
                continue

            # Invalid Prims test
            for prim_type in invalid_prim_types:
                if geo.countPrimType(prim_type) > 0:
                    invalid.append(sop_node)  # invalid_prims
                    cls.log.error(
                        "Sop node '%s' includes invalid prims of type '%s'.",
                        sop_node.path(), prim_type
                    )

        if invalid:
            return invalid
