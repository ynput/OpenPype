# -*- coding: utf-8 -*-
"""Validate mesh is static.

This plugin is part of publish process guide.
"""

import pyblish.api
from openpype.pipeline import PublishValidationError
from openpype.pipeline.publish import (
    ValidateContentsOrder,
    RepairAction,
)
from openpype.hosts.houdini.api.action import (
    SelectInvalidAction,
    SelectROPAction,
)

import hou


# Each validation can have a single repair action
# which calls the repair method
class FreezeTimeAction(RepairAction):
    label = "Freeze Time"
    icon = "ei.pause-alt"


class ValidateMeshIsStatic(pyblish.api.InstancePlugin):
    """Validate mesh is static.

    It checks if node is time dependant.
    """

    families = ["staticMesh"]
    hosts = ["houdini"]
    label = "Validate mesh is static"

    # Usually you will use this value as default
    order = ValidateContentsOrder + 0.1

    # Validation can have as many actions as you want
    # all of these actions are defined in a seperate place
    # unlike the repair action
    actions = [FreezeTimeAction, SelectInvalidAction,
               SelectROPAction]

    # overrides InstancePlugin.process()
    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            nodes = [n.path() for n in invalid]
            raise PublishValidationError(
                "See log for details. "
                "Invalid nodes: {0}".format(nodes),
                title=self.label
            )

    # This method was named get_invalid as a convention
    # it's also used by SelectInvalidAction to select
    # the returned nodes
    @classmethod
    def get_invalid(cls, instance):

        output_node = instance.data.get("output_node")
        if output_node.isTimeDependent():
            cls.log.info("Mesh is not static!")
            return [output_node]

    # what repair action expects to find and call
    @classmethod
    def repair(cls, instance):
        """Adds a time shift node.

        It should kill time dependency.
        """

        rop_node = hou.node(instance.data["instance_node"])
        # I'm doing so because an artist may change output node
        # before clicking the button.
        output_node = rop_node.parm("startnode").evalAsNode()

        if not output_node:
            cls.log.debug(
                "Action isn't performed, invalid SOP Path on %s",
                rop_node
            )
            return

        # This check to prevent the action from running multiple times.
        # git_invalid only returns [output_node] when
        #   path attribute is the problem
        if cls.get_invalid(instance) != [output_node]:
            return

        time_shift = output_node.parent().createNode("timeshift",
                                                     "freeze_time")
        time_shift.parm("frame").deleteAllKeyframes()

        frame = instance.data.get("frameStart", hou.intFrame())
        time_shift.parm("frame").set(frame)

        cls.log.debug(
            "'%s' was created. It will kill time dependency.",
            time_shift
        )

        time_shift.setGenericFlag(hou.nodeFlag.DisplayComment, True)
        time_shift.setComment(
            'This node was created automatically by '
            '"Freeze Time" Action'
            '\nFeel free to modify or replace it.'
        )

        if output_node.type().name() in ["null", "output"]:
            # Connect before
            time_shift.setFirstInput(output_node.input(0))
            time_shift.moveToGoodPosition()
            output_node.setFirstInput(time_shift)
            output_node.moveToGoodPosition()
        else:
            # Connect after
            time_shift.setFirstInput(output_node)
            rop_node.parm("startnode").set(time_shift.path())
            time_shift.moveToGoodPosition()

            cls.log.debug(
                "SOP path on '%s' updated to new output node '%s'",
                rop_node, time_shift
            )
