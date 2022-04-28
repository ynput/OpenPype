import collections
import pyblish.api
import openpype.api
from openpype.pipeline import PublishXmlValidationError


class ValidateSubsetUniqueness(pyblish.api.ContextPlugin):
    """
        Validate that all subset's names are unique.
    """

    label = "Validate Subset Uniqueness"
    hosts = ["photoshop"]
    order = openpype.api.ValidateContentsOrder
    families = ["image"]

    def process(self, context):
        subset_names = []

        for instance in context:
            self.log.info("instance:: {}".format(instance.data))
            if instance.data.get('publish'):
                subset_names.append(instance.data.get('subset'))

        non_unique = \
            [item
             for item, count in collections.Counter(subset_names).items()
             if count > 1]
        msg = ("Instance subset names {} are not unique. ".format(non_unique) +
               "Remove duplicates via SubsetManager.")
        formatting_data = {
            "non_unique": ",".join(non_unique)
        }

        if non_unique:
            raise PublishXmlValidationError(self, msg,
                                            formatting_data=formatting_data)
