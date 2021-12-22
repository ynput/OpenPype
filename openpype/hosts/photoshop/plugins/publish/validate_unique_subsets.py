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
            if instance.data.get('publish'):
                subset_names.append(instance.data.get('subset'))

        duplicates = [item
                      for item, count in
                      collections.Counter(subset_names).items()
                      if count > 1]

        if duplicates:
            duplicates_str = ",".join(duplicates)
            formatting_data = {"duplicates_str": duplicates_str}
            msg = (
                    "Instance subset names {} are not unique.".format(
                        duplicates_str) +
                    " Remove duplicates via SubsetManager."
            )
            raise PublishXmlValidationError(self, msg,
                                            formatting_data=formatting_data)
