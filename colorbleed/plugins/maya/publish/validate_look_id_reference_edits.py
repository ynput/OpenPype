from maya import cmds

import pyblish.api
import colorbleed.api


class ValidateLookIdReferenceEdits(pyblish.api.InstancePlugin):
    """Validate nodes in look have no reference edits to cbId."""

    order = colorbleed.api.ValidateContentsOrder
    families = ['colorbleed.look']
    hosts = ['maya']
    label = 'Look Id Reference Edits'
    actions = [colorbleed.api.SelectInvalidAction]

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Invalid nodes %s" % (invalid,))

    @staticmethod
    def get_invalid(instance):

        # Collect all referenced members
        referenced_nodes = []
        relationships = instance.data["lookData"]["relationships"]
        for relationship in relationships.values():
            for member in relationship['members']:
                node = member["name"]

                if cmds.referenceQuery(node, isNodeReferenced=True):
                    referenced_nodes.append(node)

        # Validate whether any has changes to 'cbId' attribute
        # TODO: optimize this query (instead of per node)
        invalid = list()
        for node in referenced_nodes:
            edits = set(cmds.referenceQuery(node, editAttrs=True))
            if "cbId" in edits:
                invalid.append(node)

        return invalid
