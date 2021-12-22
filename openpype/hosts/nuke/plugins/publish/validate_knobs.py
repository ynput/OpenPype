import nuke

import pyblish.api
import openpype.api
from openpype.pipeline import PublishXmlValidationError


class ValidateKnobs(pyblish.api.ContextPlugin):
    """Ensure knobs are consistent.

    Knobs to validate and their values comes from the

    Controlled by plugin settings that require json in following structure:
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
    actions = [openpype.api.RepairContextAction]
    optional = True

    def process(self, context):
        invalid = self.get_invalid(context, compute=True)
        if invalid:
            raise PublishXmlValidationError(
                self,
                "Found knobs with invalid values:\n{}".format(invalid),
                formatting_data={}
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

        for instance in context:
            # Filter publisable instances.
            if not instance.data["publish"]:
                continue

            # Filter families.
            families = [instance.data["family"]]
            families += instance.data.get("families", [])
            families = list(set(families) & set(cls.knobs.keys()))
            if not families:
                continue

            # Get all knobs to validate.
            knobs = {}
            for family in families:
                for preset in cls.knobs[family]:
                    knobs.update({preset: cls.knobs[family][preset]})

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
