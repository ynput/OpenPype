import pyblish.api
from openpype.api import get_errored_instances_from_context
from openpype.hosts.nuke.api.lib import (
    get_write_node_template_attr,
    get_node_path
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
            node = instance[1]
            correct_data = get_write_node_template_attr(node)
            for key, value in correct_data.items():
                node[key].setValue(value)
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

        node = instance[1]
        write_group_node = instance[0]
        correct_data = get_write_node_template_attr(write_group_node)

        check = []
        for key, value in correct_data.items():
            if key == 'file':
                padding = len(value.split('#'))
                ref_path = get_node_path(value, padding)
                n_path = get_node_path(node[key].value(), padding)
                is_not = False
                for i, path in enumerate(ref_path):
                    if (
                        str(n_path[i]) != str(path)
                        and not is_not
                    ):
                        is_not = True
                if is_not:
                    check.append([key, value, node[key].value()])

            elif str(node[key].value()) != str(value):
                check.append([key, value, node[key].value()])

        self.log.info(check)

        if check:
            self._make_error(check)

    def _make_error(self, check):
        msg = "Write node's knobs values are not correct!\n"
        dbg_msg = msg
        msg_add = "Knob `{0}` Correct: `{1}` Wrong: `{2}` \n"
        xml_msg = ""

        for item in check:
            _msg_add = msg_add.format(item[0], item[1], item[2])
            dbg_msg += _msg_add
            xml_msg += _msg_add

        raise PublishXmlValidationError(
            self, dbg_msg, formatting_data={"xml_msg": xml_msg}
        )
