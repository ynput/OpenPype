import nuke

import pyblish.api
import pype.api


class ValidateNukeWriteKnobs(pyblish.api.ContextPlugin):
    """Ensure knobs are consistent.

    Knobs to validate and their values comes from the
    "nuke/knobs.json" preset, which needs this structure:
        {
          "family": {
            "knob_name": knob_value
          }
        }
    """

    order = pyblish.api.ValidatorOrder
    label = "Knobs"
    hosts = ["nuke"]
    actions = [pype.api.RepairContextAction]
    optional = True

    def process(self, context):
        # Check for preset existence.
        if not context.data["presets"]["nuke"].get("knobs"):
            return

        invalid = self.get_invalid(context, compute=True)
        if invalid:
            raise RuntimeError(
                "Found knobs with invalid values: {}".format(invalid)
            )

    @classmethod
    def get_invalid(cls, context, compute=False):
        invalid = context.data.get("invalid_knobs", [])
        if compute:
            invalid = cls.get_invalid_knobs(context)

        return invalid

    @classmethod
    def get_invalid_knobs(cls, context):
        presets = context.data["presets"]["nuke"]["knobs"]
        invalid_knobs = []
        for instance in context:
            # Filter publisable instances.
            if not instance.data["publish"]:
                continue

            # Filter families.
            families = [instance.data["family"]]
            families += instance.data.get("families", [])
            families = list(set(families) & set(presets.keys()))
            if not families:
                continue

            # Get all knobs to validate.
            knobs = {}
            for family in families:
                for preset in presets[family]:
                    knobs.update({preset: presets[family][preset]})

            # Get invalid knobs.
            nodes = nuke.allNodes()
            for node in nodes:
                for knob in node.knobs():
                    if knob in knobs.keys():
                        expected = knobs[knob]
                        if node[knob].value() != expected:
                            invalid_knobs.append(
                                {
                                    "knob": node[knob],
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
            data["knob"].setValue(data["expected"])
