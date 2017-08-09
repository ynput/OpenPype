import maya.cmds as cmds

import pyblish.api
import colorbleed.api


class ValidateLookContents(pyblish.api.InstancePlugin):
    """Validate look instance contents

    This is invalid when the collection was unable to collect the required
    data for a look to be published correctly.

    """

    order = colorbleed.api.ValidateContentsOrder
    families = ['colorbleed.lookdev']
    hosts = ['maya']
    label = 'Look Contents'
    actions = [colorbleed.api.SelectInvalidAction]

    invalid = []
    errors = []

    def process(self, instance):
        """Process all the nodes in the instance"""

        if not instance[:]:
            raise RuntimeError("Instance is empty")

        self.get_invalid(instance)

        if self.errors:
            error_string = "\n".join(self.errors)
            raise RuntimeError("Invalid look content. "
                               "Errors : {}".format(error_string))

    @classmethod
    def get_invalid(cls, instance):
        """Get all invalid nodes"""

        attributes = list(cls.validate_lookdata_attributes(instance))
        relationships = list(cls.validate_relationships(instance))
        non_defaults = cls.validate_non_defaults(instance)

        invalid = attributes + relationships + non_defaults

        return invalid

    @classmethod
    def validate_lookdata_attributes(cls, instance):
        """Check if the lookData has the required attributes

        Args:
            instance

        """

        invalid = set()

        attributes = ["sets", "relationships", "attributes"]
        lookdata = instance.data["lookData"]
        for attr in attributes:
            if attr not in lookdata:
                cls.errors.append("Look Data has no attribute "
                                  "'{}'".format(attr))
                invalid.add(instance.name)

        return invalid

    @classmethod
    def validate_relationships(cls, instance):
        """Validate and update lookData relationships"""

        invalid = set()

        relationships = instance.data["lookData"]["relationships"]
        for relationship in relationships:
            look_name = relationship["name"]
            for key, value in relationship.items():
                if value is None:
                    cls.errors.append("{} has invalid attribute "
                                      "'{}'".format(look_name, key))

                    invalid.add(look_name)

        return invalid

    @classmethod
    def validate_non_defaults(cls, instance):
        """Check if instance content items are part of the default nodes"""

        invalid = []
        cams = ["perspShape", "topShape", "frontShape", "sideShape"]
        cameras = cmds.ls(cams, long=True)
        references = cmds.ls(referencedNodes=True)
        default_nodes = cmds.ls(defaultNodes=True, long=True)

        defaults = list(set(cameras + references + default_nodes))

        for node in cmds.ls(instance[:], long=True):
            # might be a transform of a default item listed
            if cmds.nodeType(node) == "transform":
                children = cmds.listRelatives(node,
                                              children=True,
                                              fullPath=True)
                if children:
                    node = children
                else:
                    continue

            if node in defaults:
                invalid.append(node)
                cls.errors.append("'{}' is part of Maya default "
                                  "nodes".format(node))

        return invalid
