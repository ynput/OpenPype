import json

import maya.cmds as cmds
import xgenm

import pyblish.api
from openpype.pipeline.publish import KnownPublishError


class ValidateXgen(pyblish.api.InstancePlugin):
    """Validate Xgen data."""

    label = "Validate Xgen"
    order = pyblish.api.ValidatorOrder
    host = ["maya"]
    families = ["xgen"]

    def process(self, instance):
        # Validate only xgen collections are in objectset.
        valid_nodes = set(
            instance.data["xgenNodes"] +
            cmds.ls(instance, type="transform", long=True)
        )
        invalid_nodes = [node for node in instance if node not in valid_nodes]

        if invalid_nodes:
            raise KnownPublishError(
                "Only the collection is used when publishing. Found these "
                "invalid nodes in the objectset:\n{}".format(invalid_nodes)
            )

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
