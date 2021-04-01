import pyblish.api
import openpype.api


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

        msg = (
            "Instance subset names are not unique. " +
            "Remove duplicates via SubsetManager."
        )
        assert len(subset_names) == len(set(subset_names)), msg
