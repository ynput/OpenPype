import pyblish.api
from collections import defaultdict


class ValidateSetdressNamespaces(pyblish.api.InstancePlugin):
    """Ensure namespaces are not nested"""

    label = "Validate Setdress Namespaces"
    order = pyblish.api.ValidatorOrder
    families = ["colorbleed.setdress"]

    def process(self, instance):

        self.log.info("Checking namespace for %s", instance.name)
        if self.get_invalid(instance):
            self.log.error("Nested namespaces found")

    @classmethod
    def get_invalid(cls, instance):

        from maya import cmds

        invalid = []

        namspace_lookup = defaultdict(list)
        for item in cmds.ls(instance):
            namespace, node = item.rsplit(":", 1)[0]
            namspace_lookup[namespace].append(node)

        for namespace, nodes in namspace_lookup.items():
            parts = [p for p in namespace.split(":") if p != ""]
            if len(parts) > 1:
                invalid.extend(nodes)

        return invalid
