import pymel.core as pm

import pyblish.api
import pype.api


class ValidateAttributes(pyblish.api.ContextPlugin):
    """Ensure attributes are consistent.

    Attributes to validate and their values comes from the
    "maya/attributes.json" preset, which needs this structure:
        {
          "family": {
            "node_name.attribute_name": attribute_value
          }
        }
    """

    order = pype.api.ValidateContentsOrder
    label = "Attributes"
    hosts = ["maya"]
    actions = [pype.api.RepairContextAction]
    optional = True

    def process(self, context):
        # Check for preset existence.
        if not context.data["presets"]["maya"].get("attributes"):
            return

        invalid = self.get_invalid(context, compute=True)
        if invalid:
            raise RuntimeError(
                "Found attributes with invalid values: {}".format(invalid)
            )

    @classmethod
    def get_invalid(cls, context, compute=False):
        invalid = context.data.get("invalid_attributes", [])
        if compute:
            invalid = cls.get_invalid_attributes(context)

        return invalid

    @classmethod
    def get_invalid_attributes(cls, context):
        presets = context.data["presets"]["maya"]["attributes"]
        invalid_attributes = []
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

            # Get all attributes to validate.
            attributes = {}
            for family in families:
                for preset in presets[family]:
                    [node_name, attribute_name] = preset.split(".")
                    try:
                        attributes[node_name].update(
                            {attribute_name: presets[family][preset]}
                        )
                    except KeyError:
                        attributes.update({
                            node_name: {
                                attribute_name: presets[family][preset]
                            }
                        })

            # Get invalid attributes.
            nodes = pm.ls()
            for node in nodes:
                name = node.name(stripNamespace=True)
                if name not in attributes.keys():
                    continue

                presets_to_validate = attributes[name]
                for attribute in node.listAttr():
                    names = [attribute.shortName(), attribute.longName()]
                    attribute_name = list(
                        set(names) & set(presets_to_validate.keys())
                    )
                    if attribute_name:
                        expected = presets_to_validate[attribute_name[0]]
                        if attribute.get() != expected:
                            invalid_attributes.append(
                                {
                                    "attribute": attribute,
                                    "expected": expected,
                                    "current": attribute.get()
                                }
                            )

        context.data["invalid_attributes"] = invalid_attributes
        return invalid_attributes

    @classmethod
    def repair(cls, instance):
        invalid = cls.get_invalid(instance)
        for data in invalid:
            data["attribute"].set(data["expected"])
