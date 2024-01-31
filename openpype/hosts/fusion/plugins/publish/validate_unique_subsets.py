from collections import defaultdict

import pyblish.api
from openpype.pipeline import PublishValidationError

from openpype.hosts.fusion.api.action import SelectInvalidAction


class ValidateUniqueSubsets(pyblish.api.ContextPlugin):
    """Ensure all instances have a unique subset name"""

    order = pyblish.api.ValidatorOrder
    label = "Validate Unique Subsets"
    families = ["render", "image"]
    hosts = ["fusion"]
    actions = [SelectInvalidAction]

    @classmethod
    def get_invalid(cls, context):

        # Collect instances per subset per asset
        instances_per_subset_asset = defaultdict(lambda: defaultdict(list))
        for instance in context:
            asset = instance.data.get("asset", context.data.get("asset"))
            subset = instance.data.get("subset", context.data.get("subset"))
            instances_per_subset_asset[asset][subset].append(instance)

        # Find which asset + subset combination has more than one instance
        # Those are considered invalid because they'd integrate to the same
        # destination.
        invalid = []
        for asset, instances_per_subset in instances_per_subset_asset.items():
            for subset, instances in instances_per_subset.items():
                if len(instances) > 1:
                    cls.log.warning(
                        "{asset} > {subset} used by more than "
                        "one instance: {instances}".format(
                            asset=asset,
                            subset=subset,
                            instances=instances
                        )
                    )
                    invalid.extend(instances)

        # Return tools for the invalid instances so they can be selected
        invalid = [instance.data["tool"] for instance in invalid]

        return invalid

    def process(self, context):
        invalid = self.get_invalid(context)
        if invalid:
            raise PublishValidationError("Multiple instances are set to "
                                         "the same asset > subset.",
                                         title=self.label)
