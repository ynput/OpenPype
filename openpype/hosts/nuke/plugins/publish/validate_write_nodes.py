import pyblish.api
from openpype.api import get_errored_instances_from_context
import openpype.hosts.nuke.api.lib as nlib
from openpype.hosts.nuke.api.lib import (
    get_write_node_template_attr,
    set_node_knobs_from_settings

)
from openpype.pipeline import PublishXmlValidationError


@pyblish.api.log
class RepairNukeWriteNodeAction(pyblish.api.Action):
    label = "Repair"
    on = "failed"
    icon = "wrench"

    def process(self, context, plugin):
        instances = get_errored_instances_from_context(context)

        for instance in instances:
            write_group_node = instance[0]
            # get write node from inside of group
            write_node = None
            for x in instance:
                if x.Class() == "Write":
                    write_node = x

            correct_data = get_write_node_template_attr(write_group_node)

            set_node_knobs_from_settings(write_node, correct_data["knobs"])

            self.log.info("Node attributes were fixed")


class ValidateNukeWriteNode(pyblish.api.InstancePlugin):
    """ Validate Write node's knobs.

    Compare knobs on write node inside the render group
    with settings. At the moment supporting only `file` knob.
    """

    order = pyblish.api.ValidatorOrder
    optional = True
    families = ["render"]
    label = "Write Node"
    actions = [RepairNukeWriteNodeAction]
    hosts = ["nuke"]

    def process(self, instance):
        write_group_node = instance[0]

        # get write node from inside of group
        write_node = None
        for x in instance:
            if x.Class() == "Write":
                write_node = x

        if write_node is None:
            return

        correct_data = get_write_node_template_attr(write_group_node)

        if correct_data:
            check_knobs = correct_data["knobs"]
        else:
            return

        check = []
        self.log.debug("__ write_node: {}".format(
            write_node
        ))

        for knob_data in check_knobs:
            key = knob_data["name"]
            value = knob_data["value"]
            self.log.debug("__ key: {} | value: {}".format(
                key, value
            ))
            if (
                str(write_node[key].value()) != str(value)
                and key != "file"
                and key != "tile_color"
            ):
                check.append([key, value, write_node[key].value()])

        self.log.info(check)

        if check:
            self._make_error(check)

    def _make_error(self, check):
        # sourcery skip: merge-assign-and-aug-assign, move-assign-in-block
        dbg_msg = "Write node's knobs values are not correct!\n"
        msg_add = "Knob '{0}' > Correct: `{1}` > Wrong: `{2}`"

        details = [
            msg_add.format(item[0], item[1], item[2])
            for item in check
        ]
        xml_msg = "<br/>".join(details)
        dbg_msg += "\n\t".join(details)

        raise PublishXmlValidationError(
            self, dbg_msg, formatting_data={"xml_msg": xml_msg}
        )
