import pyblish
from openpype.pipeline import PublishXmlValidationError
from openpype.hosts.nuke import api as napi
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
        with napi.maintained_selection():
            # collect all failed nodes xpos and ypos
            for instance in instances:
                grpn = instance.data["transientData"]["node"]
                nuke.showDag(grpn)


class ValidateGizmo(pyblish.api.InstancePlugin):
    """Validate amount of output nodes in gizmo (group) node"""

    order = pyblish.api.ValidatorOrder
    optional = True
    families = ["gizmo"]
    label = "Validate Gizmo (group)"
    hosts = ["nuke"]
    actions = [OpenFailedGroupNode]

    def process(self, instance):
        grpn = instance.data["transientData"]["node"]

        with grpn:
            connections_out = nuke.allNodes('Output')
            if len(connections_out) > 1:
                msg_multiple_outputs = (
                    "Only one outcoming connection from "
                    "\"{}\" is allowed").format(instance.data["name"])

                raise PublishXmlValidationError(
                    self, msg_multiple_outputs, "multiple_outputs",
                    {"node_name": grpn["name"].value()}
                )

            connections_in = nuke.allNodes('Input')
            if len(connections_in) == 0:
                msg_missing_inputs = (
                    "At least one Input node has to be inside Group: "
                    "\"{}\"").format(instance.data["name"])

                raise PublishXmlValidationError(
                    self, msg_missing_inputs, "no_inputs",
                    {"node_name": grpn["name"].value()}
                )
