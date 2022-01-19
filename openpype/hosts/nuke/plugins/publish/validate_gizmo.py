import nuke
import pyblish
from openpype.hosts.nuke.api.lib import maintained_selection


class OpenFailedGroupNode(pyblish.api.Action):
    """
    Centering failed instance node in node grap
    """

    label = "Open Gizmo in Node Graph"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):

        # Get the errored instances
        failed = []
        for result in context.data["results"]:
            if (result["error"] is not None and result["instance"] is not None
                    and result["instance"] not in failed):
                failed.append(result["instance"])

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(failed, plugin)

        # maintain selection
        with maintained_selection():
            # collect all failed nodes xpos and ypos
            for instance in instances:
                grpn = instance[0]
                nuke.showDag(grpn)


@pyblish.api.log
class ValidateGizmo(pyblish.api.InstancePlugin):
    """Validate amount of output nodes in gizmo (group) node"""

    order = pyblish.api.ValidatorOrder
    optional = True
    families = ["gizmo"]
    label = "Validate Gizmo (Group)"
    hosts = ["nuke"]
    actions = [OpenFailedGroupNode]

    def process(self, instance):
        grpn = instance[0]

        with grpn:
            connections_out = nuke.allNodes('Output')
            msg_multiple_outputs = "Only one outcoming connection from "
            "\"{}\" is allowed".format(instance.data["name"])
            assert len(connections_out) <= 1, msg_multiple_outputs

            connections_in = nuke.allNodes('Input')
            msg_missing_inputs = "At least one Input node has to be used in: "
            "\"{}\"".format(instance.data["name"])
            assert len(connections_in) >= 1, msg_missing_inputs
