import pyblish.api
import openpype.hosts.nuke.lib


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

            # Remove existing knobs.
            knob_names = openpype.hosts.nuke.lib.get_deadline_knob_names()
            for name, knob in group_node.knobs().items():
                if name in knob_names:
                    group_node.removeKnob(knob)

            openpype.hosts.nuke.lib.add_deadline_tab(group_node)


class ValidateNukeWriteDeadlineTab(pyblish.api.InstancePlugin):
    """Ensure Deadline tab is present and current."""

    order = pyblish.api.ValidatorOrder
    label = "Deadline Tab"
    hosts = ["nuke"]
    optional = True
    families = ["render"]
    actions = [RepairNukeWriteDeadlineTab]

    def process(self, instance):
        group_node = [x for x in instance if x.Class() == "Group"][0]

        knob_names = openpype.hosts.nuke.lib.get_deadline_knob_names()
        missing_knobs = []
        for name in knob_names:
            if name not in group_node.knobs().keys():
                missing_knobs.append(name)
        assert not missing_knobs, "Missing knobs: {}".format(missing_knobs)
