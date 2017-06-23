from maya import cmds

import pyblish.api
import colorbleed.api


class ValidateLookIgnoreColorSpace(pyblish.api.InstancePlugin):
    """Validate look textures are set to ignore color space when set to RAW

    Whenever the format is NOT set to sRGB for a file texture it must have
    its ignore color space file rules checkbox enabled to avoid unwanted
    reverting to sRGB settings upon file relinking.

    To fix this use the select invalid action to find the invalid file nodes
    and then check the "Ignore Color Space File Rules" checkbox under the
    Color Space settings.

    """

    order = colorbleed.api.ValidateContentsOrder
    families = ['colorbleed.look']
    hosts = ['maya']
    label = 'Look RAW Ignore color space'
    actions = [colorbleed.api.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance):

        # Get texture nodes from the collected resources
        required = ["maya", "look", "attribute"]
        nodes = list()
        for resource in instance.data.get("resources", []):
            if all(tag in resource.get("tags", []) for tag in required):
                node = resource['node']
                nodes.append(node)

        nodes = list(sorted(set(nodes)))
        cls.log.info("Checking nodes: {0}".format(nodes))

        # Validate
        invalid = []
        for node in nodes:
            color_space = cmds.getAttr(node + ".colorSpace")
            ignore_rules = cmds.getAttr(node + ".ignoreColorSpaceFileRules")
            if color_space != "sRGB" and not ignore_rules:
                invalid.append(node)

        return invalid

    def process(self, instance):
        """Process all the nodes in the instance"""

        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Non-sRGB file textures nodes with ignore "
                               "color space file rules disabled: "
                               "{0}".format(invalid))
