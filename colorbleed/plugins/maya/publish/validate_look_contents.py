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
    label = 'Look Data Contents'
    actions = [colorbleed.api.SelectInvalidAction]

    def process(self, instance):
        """Process all the nodes in the instance"""

        if not instance[:]:
            raise RuntimeError("Instance is empty")

        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Invalid look content")

    @classmethod
    def get_invalid(cls, instance):
        """Get all invalid nodes"""

        attributes = list(cls.validate_lookdata_attributes(instance))
        relationships = list(cls.validate_relationship_ids(instance))

        invalid = attributes + relationships

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
                cls.log.error("Look Data has no attribute "
                              "'{}'".format(attr))
                invalid.add(instance.name)

        if not lookdata["relationships"] or not lookdata["sets"]:
            cls.log.error("Look has no `relationship` or `sets`")
            invalid.add(instance.name)

        return invalid

    @classmethod
    def validate_relationship_ids(cls, instance):
        """Validate and update lookData relationships"""

        invalid = set()

        relationships = instance.data["lookData"]["relationships"]
        for relationship in relationships:
            look_name = relationship["name"]
            uuid = relationship["uuid"]
            if not uuid:
                cls.errors.append("{} has invalid ID ")
                invalid.add(look_name)

        return invalid
