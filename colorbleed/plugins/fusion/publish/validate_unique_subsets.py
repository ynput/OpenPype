import pyblish.api


class ValidateUniqueSubsets(pyblish.api.InstancePlugin):
    """Ensure all instances have a unique subset name"""

<<<<<<< HEAD:colorbleed/plugins/fusion/publish/validate_unique_name.py
    order = pyblish.api.ValidatorOrder + 0.1
    label = "Validate Unique Subset Names"
    families = ["colorbleed.imagesequence"]
=======
    order = pyblish.api.ValidatorOrder
    label = "Validate Unique Subsets"
    families = ["colorbleed.saver"]
>>>>>>> 1e4234f45691f328f3d347c326c017e00979ec57:colorbleed/plugins/fusion/publish/validate_unique_subsets.py
    hosts = ["fusion"]

    @classmethod
    def get_invalid(cls, instance):

        context = instance.context
        subset = instance.data["subset"]
        for other_instance in context[:]:
            if other_instance == instance:
                continue

            if other_instance.data["subset"] == subset:
                return [instance]   # current instance is invalid

        return []

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Animation content is invalid. See log.")
