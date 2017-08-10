import maya.cmds as cmds

import pyblish.api
import colorbleed.api
import colorbleed.maya.lib as lib


class ValidateLookContents(pyblish.api.InstancePlugin):
    """Validate look instance contents

    This is invalid when the collection was unable to collect the required
    data for a look to be published correctly.

    """

    order = colorbleed.api.ValidateContentsOrder
    families = ['colorbleed.lookdev']
    hosts = ['maya']
    label = 'Look Data Contents'
    actions = [colorbleed.api.SelectInvalidAction]

    def process(self, instance):
        """Process all the nodes in the instance"""

        if not instance[:]:
            raise RuntimeError("Instance is empty")

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("'{}' has invalid look "
                               "content".format(instance.name))

    @classmethod
    def get_invalid(cls, instance):
        """Get all invalid nodes"""

        cls.log.info("Validating look content for "
                     "'{}'".format(instance.name))

        instance_items = cls.validate_instance_items(instance)
        attributes = list(cls.validate_lookdata_attributes(instance))
        relationships = list(cls.validate_relationship_ids(instance))

        invalid = instance_items + attributes + relationships

        return invalid

    @classmethod
    def validate_lookdata_attributes(cls, instance):
        """Check if the lookData has the required attributes

        Args:
            instance

        """

        invalid = set()

        attributes = ["relationships", "attributes"]
        lookdata = instance.data["lookData"]
        for attr in attributes:
            if attr not in lookdata:
                cls.log.error("Look Data has no attribute "
                              "'{}'".format(attr))
                invalid.add(instance.name)

        # Validate at least one single relationship is collected
        if not lookdata["relationships"]:
            cls.log.error("Look '{}' has no "
                          "`relationship`".format(instance.name))
            invalid.add(instance.name)

        return invalid

    @classmethod
    def validate_relationship_ids(cls, instance):
        """Validate and update lookData relationships"""

        invalid = set()

        relationships = instance.data["lookData"]["relationships"]
        for objectset, members in relationships.items():
            uuid = members["uuid"]
            if not uuid:
                look_name = objectset
                cls.log.error("{} has invalid ID ".format(look_name))
                invalid.add(look_name)

        return invalid

    @classmethod
    def validate_instance_items(cls, instance):

        required_nodes = lib.get_id_required_nodes(referenced_nodes=False)

        invalid = [node for node in instance if node in required_nodes
                   and not lib.get_id(node)]
        if invalid:
            nr_of_invalid = len(invalid)
            cls.log.error("Found {} nodes without ID: {}".format(nr_of_invalid,
                                                                 invalid))
        return invalid



