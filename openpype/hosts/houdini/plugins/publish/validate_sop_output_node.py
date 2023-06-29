# -*- coding: utf-8 -*-
import pyblish.api
from openpype.pipeline import PublishValidationError
from openpype.pipeline.publish import RepairAction

import hou

class ValidateSopOutputNode(pyblish.api.InstancePlugin):
    """Validate the instance SOP Output Node.

    This will ensure:
        - The SOP Path is set.
        - The SOP Path refers to an existing object.
        - The SOP Path node is a SOP node.
        - The SOP Path node is a SOP Output node.
        - The SOP Path node has at least one input connection (has an input)
        - The SOP Path has geometry data.

    """

    order = pyblish.api.ValidatorOrder
    families = ["pointcache", "vdbcache"]
    hosts = ["houdini"]
    label = "Validate Output Node"
    actions = [RepairAction]

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "Output node(s) are incorrect",
                title="Invalid output node(s)"
            )

    @classmethod
    def get_invalid(cls, instance):

        output_node = instance.data.get("output_node")

        if output_node is None:
            node = hou.node(instance.data["instance_node"])
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

        # Output node must be a Sop Output node.
        if not output_node.type().name() == "output":
            cls.log.error(
                "Output node %s is not a SOP Output node. "
                "SOP Path must point to a SOP Output node, "
                "instead found sop type: '%s'"
                % (output_node.path(), output_node.type().name())
            )
            return [output_node.path()]

        # For the sake of completeness also assert the category type
        # is Sop to avoid potential edge case scenarios even though
        # the isinstance check above should be stricter than this category
        if output_node.type().category().name() != "Sop":
            raise PublishValidationError(
                ("Output node {} is not of category Sop. "
                 "This is a bug.").format(output_node.path()),
                title=cls.label)

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

    @classmethod
    def repair(cls, instance):
        """Repair action if SOP Output node wasn't exist.

        If output_node is not None, It will create a SOP Output node,
        connect it to the node with render flag, and then fix
        ROP's sop_path or soppath parameter accordingly.
        """

        output_node = instance.data.get("output_node")
        rop_node = hou.node(instance.data["instance_node"])
        if rop_node.type().name() == "alembic":
            sop_path_value = rop_node.parm("sop_path").eval()
            # if ROP sop_path is empty
            if not sop_path_value:
                cls.log.debug("This ROP '%s' has empty SOP Path"% rop_node.path())
                cls.log.debug("Try Setting SOP path to selected node")
                sop_path_value = cls.get_selected_node_path()
                if not sop_path_value:
                    cls.log.debug("Please Select a valid obj or node and click \
repair again.")
                    return

            # if ROP sop_path is pointing to a node that no longer exists
            if not hou.node(sop_path_value):
                # I will just assume they deleted output node by accident
                cls.log.debug("SOP Path parm of this ROP '%s' points to a non \
                               existed node" % rop_node.path())
                cls.log.debug("'%s' doesn't exist" % sop_path_value)

                sop_path_value = sop_path_value.rstrip('/')
                sop_path_value = '/'.join(sop_path_value.split('/')[:-1])
                cls.log.debug("Trying setting sop path to the parent '%s'" \
% sop_path_value)

                if not isinstance(hou.node(sop_path_value), hou.ObjNode):
                    cls.log.debug("'%s' is not valid or it doesn't exist!" \
% sop_path_value)
                    rop_node.parm('sop_path').set("")
                    cls.log.debug("Resetting SOP Path of this ROP '%s'" \
% rop_node.path())

                    cls.log.debug("Try Setting SOP path to selected node")
                    sop_path_value = cls.get_selected_node_path()
                    if not sop_path_value:
                        cls.log.debug("Please Select a valid obj or node and click \
repair again.")
                        return

            # Re-read SOP path as output node to read the last updated value
            # As it won't be updated in this code scope until publisher is refereshed
            output_node = hou.node(sop_path_value)

            if isinstance(output_node, hou.SopNode):

                if output_node.type().name() == "output":
                    cls.log.debug("SOP Path points to a Sop Output node")
                    rop_node.parm('sop_path').set(output_node.path())
                    cls.log.debug("SOP Output node is set.")
                else:
                    cls.log.debug("SOP Path points to an Sop node and it isn't \
a SOP Output node")

                    sop_output = cls.get_sop_output_node(output_node.parent())
                    rop_node.parm('sop_path').set(sop_output.path())
                    cls.log.debug("SOP Output node is set.")

            elif isinstance(output_node, hou.ObjNode):
                cls.log.debug("SOP Path points to an Obj node")
                sop_output = cls.get_sop_output_node(output_node)

                rop_node.parm('sop_path').set(sop_output.path())
                cls.log.debug("SOP Output node is set.")

        else:
            cls.log.warning("Only alembic ROP works for now.")

    @classmethod
    def get_sop_output_node(cls, parent_node):
        child_render = ""
        sop_output = ""
        # try to find output node
        for child in parent_node.children():
            if child.isGenericFlagSet(hou.nodeFlag.Render):
                child_render = child
            if child.type().name() == "output":
                sop_output = child
                break

        # create output node if not exists
        if not sop_output:
            sop_output = parent_node.createNode("output", "OUTPUT")
            sop_output.setFirstInput(child_render)

        sop_output.setDisplayFlag(1)
        sop_output.setRenderFlag(1)
        sop_output.moveToGoodPosition()

        return sop_output

    @classmethod
    def get_selected_node_path(cls):
        selected_nodes = hou.selectedNodes()
        if selected_nodes:
            selected_node = selected_nodes[0]

            if isinstance(selected_node, hou.ObjNode) or \
                isinstance(selected_node, hou.SopNode):

                cls.log.debug("%s was selected" % selected_node.path())
                return selected_node.path()

        return
