import json

import maya.cmds as cmds
import xgenm

import pyblish.api
from openpype.pipeline.publish import PublishValidationError


class ValidateXgen(pyblish.api.InstancePlugin):
    """Validate Xgen data."""

    label = "Validate Xgen"
    order = pyblish.api.ValidatorOrder
    host = ["maya"]
    families = ["xgen"]

    def process(self, instance):
        set_members = instance.data.get("setMembers")

        # Only 1 collection/node per instance.
        if len(set_members) != 1:
            raise PublishValidationError(
                "Only one collection per instance is allowed."
                " Found:\n{}".format(set_members)
            )

        # Only xgen palette node is allowed.
        node_type = cmds.nodeType(set_members[0])
        if node_type != "xgmPalette":
            raise PublishValidationError(
                "Only node of type \"xgmPalette\" are allowed. Referred to as"
                " \"collection\" in the Maya UI."
                " Node type found: {}".format(node_type)
            )

        # Cant have inactive modifiers in collection cause Xgen will try and
        # look for them when loading.
        palette = instance.data["xgmPalette"].replace("|", "")
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

        if inactive_modifiers:
            raise PublishValidationError(
                "There are inactive modifiers on the collection. "
                "Please delete these:\n{}".format(
                    json.dumps(inactive_modifiers, indent=4, sort_keys=True)
                )
            )

        # We need a namespace else there will be a naming conflict when
        # extracting because of stripping namespaces and parenting to world.
        node_names = [instance.data["xgmPalette"]]
        for _, connections in instance.data["xgenConnections"].items():
            node_names.append(connections["transform"].split(".")[0])

        non_namespaced_nodes = [n for n in node_names if ":" not in n]
        if non_namespaced_nodes:
            raise PublishValidationError(
                "Could not find namespace on {}. Namespace is required for"
                " xgen publishing.".format(non_namespaced_nodes)
            )
