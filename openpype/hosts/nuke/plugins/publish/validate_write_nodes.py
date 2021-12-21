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
            for k, v in correct_data.items():
                node[k].setValue(v)
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
        correct_data = get_write_node_template_attr(node)

        check = []
        for k, v in correct_data.items():
            if k is 'file':
                padding = len(v.split('#'))
                ref_path = get_node_path(v, padding)
                n_path = get_node_path(node[k].value(), padding)
                isnt = False
                for i, p in enumerate(ref_path):
                    if str(n_path[i]) not in str(p):
                        if not isnt:
                            isnt = True
                        else:
                            continue
                if isnt:
                    check.append([k, v, node[k].value()])
            else:
                if str(node[k].value()) not in str(v):
                    check.append([k, v, node[k].value()])

        self.log.info(check)

        msg = "Write node's knobs values are not correct!\n"
        msg_add = "Knob `{0}` Correct: `{1}` Wrong: `{2}` \n"
        xml_msg = ""

        if check:
            dbg_msg = msg
            for item in check:
                _msg_add = msg_add.format(item[0], item[1], item[2])
                dbg_msg += _msg_add
                xml_msg += _msg_add

            raise PublishXmlValidationError(
                self, dbg_msg, {"xml_msg": xml_msg}
            )
