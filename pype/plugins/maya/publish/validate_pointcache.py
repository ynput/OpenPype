import pyblish.api

import pype.api
import pype.hosts.maya.action


class ValidatePointcache(pyblish.api.InstancePlugin):
    """Validate pointcache content."""

    order = pype.api.ValidateContentsOrder
    label = "Pointcache"
    hosts = ["maya"]
    families = ["pointcache"]
    actions = [pype.hosts.maya.action.SelectInvalidAction]

    @classmethod
    def get_invalid(cls, instance, compute=False):
        invalid = []
        if compute:
            names = {}
            for node in instance:
                node_name = node.split("|")[-1]
                try:
                    names[node_name].append(node)
                except KeyError:
                    names[node_name] = [node]

            instance.data["invalid"] = []
            for name, nodes in names.items():
                if len(nodes) != 1:
                    invalid.extend(nodes)
                    instance.data["invalid"].extend(nodes)
        else:
            invalid.extend(instance.data["invalid"])

        return invalid

    def process(self, instance):
        invalid = self.get_invalid(instance, compute=True)
        if invalid:
            raise RuntimeError(
                "Meshes found is duplicate names: {}".format(invalid)
            )
