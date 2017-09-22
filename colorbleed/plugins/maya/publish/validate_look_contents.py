import pyblish.api
import colorbleed.api


class ValidateLookContents(pyblish.api.InstancePlugin):
    """Validate look instance contents

    Rules:
        * Look data must have `relationships` and `attributes` keys.
        * At least one relationship must be collection.
        * All relationship object sets at least have an ID value

    """

    order = colorbleed.api.ValidateContentsOrder
    families = ['colorbleed.look']
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

        # check if data has the right attributes and content
        attributes = cls.validate_lookdata_attributes(instance)
        # check the looks for ID
        looks = cls.validate_looks(instance)

        invalid = looks + attributes

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
                          "`relationships`".format(instance.name))
            invalid.add(instance.name)

        return list(invalid)

    @classmethod
    def validate_looks(cls, instance):

        looks = instance.data["lookData"]["relationships"]
        invalid = []
        for name, data in looks.items():
            if not data["uuid"]:
                cls.log.error("Look '{}' has no UUID".format(name))
                invalid.append(name)

        return invalid
