import pyblish.api
import pype.nuke.lib


class RepairNukeWriteDeadlineTab(pyblish.api.Action):

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
            group_node = [x for x in instance if x.Class() == "Group"][0]
            pype.nuke.lib.add_deadline_tab(group_node)


class ValidateNukeWriteDeadlineTab(pyblish.api.InstancePlugin):
    """Ensure Deadline tab is present and current."""

    order = pyblish.api.ValidatorOrder
    label = "Deadline Tab"
    hosts = ["nuke"]
    optional = True
    families = ["write"]
    actions = [RepairNukeWriteDeadlineTab]

    def process(self, instance):
        group_node = [x for x in instance if x.Class() == "Group"][0]

        msg = "Deadline tab missing on \"{}\"".format(group_node.name())
        assert "Deadline" in group_node.knobs(), msg
