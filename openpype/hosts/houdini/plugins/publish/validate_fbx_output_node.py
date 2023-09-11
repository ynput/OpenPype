# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
from openpype.hosts.houdini.api.action import (
    SelectInvalidAction,
    SelectROPAction,
)
from openpype.hosts.houdini.api.lib import get_obj_node_output
from collections import defaultdict
import hou


class ValidateFBXOutputNode(pyblish.api.InstancePlugin):
    """Validate the instance Output Node.

    This will ensure:
        - The Output Node Path is set.
        - The Output Node Path refers to an existing object.
        - The Output Node is a Sop or Obj node.
        - The Output Node has geometry data.
    """

    order = pyblish.api.ValidatorOrder
    families = ["fbx"]
    hosts = ["houdini"]
    label = "Validate FBX Output Node"
    actions = [SelectROPAction, SelectInvalidAction]

    def process(self, instance):

        invalid = self.get_invalid_categorized(instance)
        if invalid:
            raise PublishValidationError(
                "Output node(s) are incorrect",
                title="Invalid output node(s)"
            )
    @classmethod
    def get_invalid(cls, instance):
        out = cls.get_invalid_categorized(instance).values()
        invalid = []
        for row in out:
            invalid += row
        return invalid


    @classmethod
    def get_invalid_categorized(cls, instance):
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

        # Check if the Output Node is a Sop or Obj node
        #  also, make a dictionary of all geo obj nodes
        #  and their sop output node.
        all_outputs = {}
        # if user selects an ObjSubnet or an ObjNetwork
        if output_node.childTypeCategory() == hou.objNodeTypeCategory():
            all_outputs.update({output_node : {}})
            for node in output_node.allSubChildren():
                if node.type().name() == "geo":
                    out = get_obj_node_output(node)
                    all_outputs[output_node].update({node: out})

        # elif user selects a geometry ObjNode
        elif output_node.type().name() == "geo":
            out = get_obj_node_output(output_node)
            all_outputs.update({output_node: out})

        # elif user selects a SopNode
        elif output_node.type().category().name() == "Sop":
            # expetional case because output_node is not an obj node
            all_outputs.update({output_node: output_node})

        # Then it's wrong node type
        else:
            cls.log.error(
                "Output node %s is not a SOP or OBJ Geo or OBJ SubNet node. "
                "Instead found category type: %s %s"
                , output_node.path(), output_node.type().category().name()
                , output_node.type().name()
            )
            return [output_node]

        # Check if geo obj node have geometry.
        #  return geo obj node if their sop output node
        valid = {}
        invalid = defaultdict(list)
        cls.filter_inner_dict(all_outputs, valid, invalid)

        invalid_prim_types = ["VDB", "Volume"]
        for obj_node, sop_node in valid.items():
            # Empty Geometry test
            if not hasattr(sop_node, "geometry"):
                invalid["empty_geometry"].append(sop_node)
                cls.log.error(
                    "Sop node '%s' includes no geometry."
                    , sop_node.path()
                )
                continue

            frame = instance.data.get("frameStart", 0)
            geo = sop_node.geometryAtFrame(frame)
            if len(geo.iterPrims()) == 0:
                invalid["empty_geometry"].append(sop_node)
                cls.log.error(
                    "Sop node '%s' includes no geometry."
                    , sop_node.path()
                )
                continue

            # Invalid Prims test
            for prim_type in invalid_prim_types:
                if geo.countPrimType(prim_type) > 0:
                    invalid["invalid_prims"].append(sop_node)
                    cls.log.error(
                        "Sop node '%s' includes invliad prims of type '%s'."
                        , sop_node.path(), prim_type
                    )

        if invalid:
            return invalid

    @classmethod
    def filter_inner_dict(cls, d: dict, valid: dict, invalid: dict):
        """Parse the dictionary and filter items to valid and invalid.

        Invalid items have empty values like {}, None
        Valid dictionary is a flattened dictionary that includes
          the valid inner items.
        """

        for k, v in d.items():
            if not v:
                invalid["empty_objs"].append(k)
            elif isinstance(v, dict):
                cls.filter_inner_dict(v, valid, invalid)
            else:
                valid.update({k:v})
