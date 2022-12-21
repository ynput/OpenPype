import json

import maya.cmds as cmds
import xgenm

import pyblish.api


class ValidateXgen(pyblish.api.InstancePlugin):
    """Validate Xgen data."""

    label = "Validate Xgen"
    order = pyblish.api.ValidatorOrder
    host = ["maya"]
    families = ["xgen"]

    def process(self, instance):
        # Validate only xgen collections are in objectset.
        nodes = set(
            instance.data["xgenNodes"] +
            cmds.ls(instance, type="transform", long=True)
        )
        remainder_nodes = []
        for node in instance:
            if node in nodes:
                continue
            remainder_nodes.append(node)

        msg = "Invalid nodes in the objectset:\n{}".format(remainder_nodes)
        assert not remainder_nodes, msg

        # Only one collection per instance.
        palette_amount = len(instance.data["xgenPalettes"])
        msg = "Only one collection per instance allow. Found {}:\n{}".format(
            palette_amount, instance.data["xgenPalettes"]
        )
        assert palette_amount == 1, msg

        # Cant have inactive modifiers in collection cause Xgen will try and
        # look for them when loading.
        palette = instance.data["xgenPalette"].replace("|", "")
        inactive_modifiers = {}
        for description in instance.data["xgmDescriptions"]:
            description = description.split("|")[-2]
            modifier_names = xgenm.fxModules(palette, description)
            for name in modifier_names:
                attr = xgenm.getAttr("active", palette, description, name)
                # Attribute value are lowercase strings of false/true.
                if attr == "false":
                    try:
                        inactive_modifiers[description].append(name)
                    except KeyError:
                        inactive_modifiers[description] = [name]

        msg = (
            "There are inactive modifiers on the collection. "
            "Please delete these:\n{}".format(
                json.dumps(inactive_modifiers, indent=4, sort_keys=True)
            )
        )
        assert not inactive_modifiers, msg
