import nuke

import pyblish.api
import pype.api


class ValidateKnobs(pyblish.api.ContextPlugin):
    """Ensure knobs are consistent.

    Knobs to validate and their values comes from the

    Example for presets in config:
    "presets/plugins/nuke/publish.json" preset, which needs this structure:
        "ValidateKnobs": {
            "enabled": true,
            "knobs": {
                "family": {
                    "knob_name": knob_value
                    }
                }
            }
    """

    order = pyblish.api.ValidatorOrder
    label = "Validate Knobs"
    hosts = ["nuke"]
    actions = [pype.api.RepairContextAction]
    optional = True

    def process(self, context):
        nuke_presets = context.data["presets"].get("nuke")

        if not nuke_presets:
            return

        publish_presets = nuke_presets.get("publish")

        if not publish_presets:
            return

        plugin_preset = publish_presets.get("ValidateKnobs")

        if not plugin_preset:
            return

        invalid = self.get_invalid(context, compute=True)
        if invalid:
            raise RuntimeError(
                "Found knobs with invalid values:\n{}".format(invalid)
            )

    @classmethod
    def get_invalid(cls, context, compute=False):
        invalid = context.data.get("invalid_knobs", [])
        if compute:
            invalid = cls.get_invalid_knobs(context)

        return invalid

    @classmethod
    def get_invalid_knobs(cls, context):
        invalid_knobs = []
        publish_presets = context.data["presets"]["nuke"]["publish"]
        knobs_preset = publish_presets["ValidateKnobs"]["knobs"]
        for instance in context:
            # Filter publisable instances.
            if not instance.data["publish"]:
                continue

            # Filter families.
            families = [instance.data["family"]]
            families += instance.data.get("families", [])
            families = list(set(families) & set(knobs_preset.keys()))
            if not families:
                continue

            # Get all knobs to validate.
            knobs = {}
            for family in families:
                for preset in knobs_preset[family]:
                    knobs.update({preset: knobs_preset[family][preset]})

            # Get invalid knobs.
            nodes = []

            for node in nuke.allNodes():
                nodes.append(node)
                if node.Class() == "Group":
                    node.begin()
                    for i in nuke.allNodes():
                        nodes.append(i)
                    node.end()

            for node in nodes:
                for knob in node.knobs():
                    if knob not in knobs.keys():
                        continue

                    expected = knobs[knob]
                    if node[knob].value() != expected:
                        invalid_knobs.append(
                            {
                                "knob": node[knob],
                                "name": node[knob].name(),
                                "label": node[knob].label(),
                                "expected": expected,
                                "current": node[knob].value()
                            }
                        )

        context.data["invalid_knobs"] = invalid_knobs
        return invalid_knobs

    @classmethod
    def repair(cls, instance):
        invalid = cls.get_invalid(instance)
        for data in invalid:
            if isinstance(data["expected"], unicode):
                data["knob"].setValue(str(data["expected"]))
                continue

            data["knob"].setValue(data["expected"])
