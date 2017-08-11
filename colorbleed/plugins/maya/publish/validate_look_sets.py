from colorbleed.maya import lib

import pyblish.api
import colorbleed.api


class ValidateLookSets(pyblish.api.InstancePlugin):
    """Validate if any sets are missing from the instance and look data

    """

    order = colorbleed.api.ValidateContentsOrder
    families = ['colorbleed.lookdev']
    hosts = ['maya']
    label = 'Look Sets'
    actions = [colorbleed.api.SelectInvalidAction]

    def process(self, instance):
        """Process all the nodes in the instance"""

        if not instance[:]:
            raise RuntimeError("Instance is empty")

        self.log.info("Validation '{}'".format(instance.name))
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("'{}' has invalid look "
                               "content".format(instance.name))

    @classmethod
    def get_invalid(cls, instance):
        """Get all invalid nodes"""

        cls.log.info("Validating look content for "
                     "'{}'".format(instance.name))

        lookdata = instance.data["lookData"]
        relationships = lookdata["relationships"]

        invalid = []
        for node in instance:
            sets = lib.get_related_sets(node)
            if not sets:
                continue

            missing_sets = [s for s in sets if s not in relationships]
            if missing_sets:
                # A set of this node is not coming along, this is wrong!
                cls.log.error("Missing sets '{}' for node "
                              "'{}'".format(missing_sets, node))
                invalid.append(node)
                continue

            # Ensure the node is in the sets that are collected
            for shaderset, data in relationships.items():
                if shaderset not in sets:
                    # no need to check for a set if the node
                    # isn't in it anyway
                    continue

                member_nodes = [member['name'] for member in data['members']]
                if node not in member_nodes:
                    # The node is not found in the collected set
                    # relationships
                    cls.log.error("Missing '{}' in collected set node "
                                  "'{}'".format(node, shaderset))
                    invalid.append(node)

                    continue

        return invalid


