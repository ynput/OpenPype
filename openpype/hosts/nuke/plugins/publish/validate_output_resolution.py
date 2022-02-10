import nuke

import pyblish.api


class RepairWriteResolutionDifference(pyblish.api.Action):

    label = "Repair"
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

        for instance in instances:
            reformat = instance[0].dependencies()[0]
            if reformat.Class() != "Reformat":
                reformat = nuke.nodes.Reformat(inputs=[instance[0].input(0)])

                xpos = instance[0].xpos()
                ypos = instance[0].ypos() - 26

                dependent_ypos = instance[0].dependencies()[0].ypos()
                if (instance[0].ypos() - dependent_ypos) <= 51:
                    xpos += 110

                reformat.setXYpos(xpos, ypos)

                instance[0].setInput(0, reformat)

            reformat["resize"].setValue("none")


class ValidateOutputResolution(pyblish.api.InstancePlugin):
    """Validates Output Resolution.

    It is making sure the resolution of write's input is the same as
    Format definition of script in Root node.
    """

    order = pyblish.api.ValidatorOrder
    optional = True
    families = ["render", "render.local", "render.farm"]
    label = "Write Resolution"
    hosts = ["nuke"]
    actions = [RepairWriteResolutionDifference]

    def process(self, instance):

        # Skip bounding box check if a reformat node exists.
        if instance[0].dependencies()[0].Class() == "Reformat":
            return

        msg = "Bounding box is outside the format."
        assert self.check_resolution(instance), msg

    def check_resolution(self, instance):
        node = instance[0]

        root_width = instance.data["resolutionWidth"]
        root_height = instance.data["resolutionHeight"]

        write_width = node.format().width()
        write_height = node.format().height()

        if (root_width != write_width) or (root_height != write_height):
            return None
        else:
            return True
