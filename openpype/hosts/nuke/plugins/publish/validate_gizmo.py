import pyblish
from openpype.pipeline import PublishXmlValidationError
from openpype.hosts.nuke.api import maintained_selection
import nuke


class OpenFailedGroupNode(pyblish.api.Action):
    """
    Centering failed instance node in node grap
    """

    label = "Open Group"
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
            msg_multiple_outputs = (
                "Only one outcoming connection from "
                "\"{}\" is allowed").format(instance.data["name"])

            if len(connections_out) > 1:
                raise PublishXmlValidationError(
                    self, msg_multiple_outputs, "multiple_outputs",
                    {"node_name": grpn["name"].value()}
                )

            connections_in = nuke.allNodes('Input')
            msg_missing_inputs = (
                "At least one Input node has to be inside Group: "
                "\"{}\"").format(instance.data["name"])

            if len(connections_in) == 0:
                raise PublishXmlValidationError(
                    self, msg_missing_inputs, "no_inputs",
                    {"node_name": grpn["name"].value()}
                )
