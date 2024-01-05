from collections import defaultdict
import pyblish.api
from openpype.pipeline.publish import (
    PublishXmlValidationError,
)


class ValidateSubsetUniqueness(pyblish.api.ContextPlugin):
    """Validate all subset names are unique.

    This only validates whether the instances currently set to publish from
    the workfile overlap one another for the asset + subset they are publishing
    to.

    This does not perform any check against existing publishes in the database
    since it is allowed to publish into existing subsets resulting in
    versioning.

    A subset may appear twice to publish from the workfile if one
    of them is set to publish to another asset than the other.

    """

    label = "Validate Subset Uniqueness"
    order = pyblish.api.ValidatorOrder
    families = ["*"]

    def process(self, context):

        # Find instance per (asset,subset)
        instance_per_asset_subset = defaultdict(list)
        for instance in context:

            # Ignore disabled instances
            if not instance.data.get('publish', True):
                continue

            # Ignore instance without asset data
            asset = instance.data.get("asset")
            if asset is None:
                self.log.warning("Instance found without `asset` data: "
                                 "{}".format(instance.name))
                continue

            # Ignore instance without subset data
            subset = instance.data.get("subset")
            if subset is None:
                self.log.warning("Instance found without `subset` data: "
                                 "{}".format(instance.name))
                continue

            instance_per_asset_subset[(asset, subset)].append(instance)

        non_unique = []
        for (asset, subset), instances in instance_per_asset_subset.items():

            # A single instance per asset, subset is fine
            if len(instances) < 2:
                continue

            non_unique.append("{asset} > {subset}".format(asset=asset,
                                                          subset=subset))

        if not non_unique:
            # All is ok
            return

        msg = ("Instance subset names {} are not unique. ".format(non_unique) +
               "Please remove or rename duplicates.")
        formatting_data = {
            "non_unique": ",".join(non_unique)
        }

        if non_unique:
            raise PublishXmlValidationError(self, msg,
                                            formatting_data=formatting_data)
