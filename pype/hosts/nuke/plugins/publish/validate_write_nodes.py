import os
import pyblish.api
import pype.utils
import pype.hosts.nuke.lib as nukelib
import avalon.nuke

@pyblish.api.log
class RepairNukeWriteNodeAction(pyblish.api.Action):
    label = "Repair"
    on = "failed"
    icon = "wrench"

    def process(self, context, plugin):
        instances = pype.utils.filter_instances(context, plugin)

        for instance in instances:
            node = instance[1]
            correct_data = nukelib.get_write_node_template_attr(node)
            for k, v in correct_data.items():
                node[k].setValue(v)
            self.log.info("Node attributes were fixed")


class ValidateNukeWriteNode(pyblish.api.InstancePlugin):
    """ Validates file output. """

    order = pyblish.api.ValidatorOrder
    optional = True
    families = ["render"]
    label = "Write Node"
    actions = [RepairNukeWriteNodeAction]
    hosts = ["nuke"]

    def process(self, instance):

        node = instance[1]
        correct_data = nukelib.get_write_node_template_attr(node)

        check = []
        for k, v in correct_data.items():
            if k is 'file':
                padding = len(v.split('#'))
                ref_path = avalon.nuke.lib.get_node_path(v, padding)
                n_path = avalon.nuke.lib.get_node_path(node[k].value(), padding)
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

        msg = "Node's attribute `{0}` is not correct!\n" \
              "\nCorrect: `{1}` \n\nWrong: `{2}` \n\n"

        if check:
            print_msg = ""
            for item in check:
                print_msg += msg.format(item[0], item[1], item[2])
            print_msg += "`RMB` click to the validator and `A` to fix!"

        assert not check, print_msg
