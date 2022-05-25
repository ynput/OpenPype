import nuke
import pyblish
from openpype.hosts.nuke.api.lib import maintained_selection
from openpype.pipeline import PublishXmlValidationError


class SelectCenterInNodeGraph(pyblish.api.Action):
    """
    Centering failed instance node in node grap
    """

    label = "Center node in node graph"
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

        all_xC = list()
        all_yC = list()

        # maintain selection
        with maintained_selection():
            # collect all failed nodes xpos and ypos
            for instance in instances:
                bdn = instance[0]
                xC = bdn.xpos() + bdn.screenWidth() / 2
                yC = bdn.ypos() + bdn.screenHeight() / 2

                all_xC.append(xC)
                all_yC.append(yC)

        self.log.info("all_xC: `{}`".format(all_xC))
        self.log.info("all_yC: `{}`".format(all_yC))

        # zoom to nodes in node graph
        nuke.zoom(2, [min(all_xC), min(all_yC)])


@pyblish.api.log
class ValidateBackdrop(pyblish.api.InstancePlugin):
    """Validate amount of nodes on backdrop node in case user
    forgotten to add nodes above the publishing backdrop node"""

    order = pyblish.api.ValidatorOrder
    optional = True
    families = ["nukenodes"]
    label = "Validate Backdrop"
    hosts = ["nuke"]
    actions = [SelectCenterInNodeGraph]

    def process(self, instance):
        connections_out = instance.data["nodeConnectionsOut"]

        msg_multiple_outputs = (
            "Only one outcoming connection from "
            "\"{}\" is allowed").format(instance.data["name"])

        if len(connections_out.keys()) > 1:
            raise PublishXmlValidationError(
                self,
                msg_multiple_outputs,
                "multiple_outputs"
            )

        msg_no_nodes = "No content on backdrop node: \"{}\"".format(
            instance.data["name"])

        if len(instance) == 0:
            raise PublishXmlValidationError(
                self,
                msg_no_nodes,
                "no_nodes"
            )
