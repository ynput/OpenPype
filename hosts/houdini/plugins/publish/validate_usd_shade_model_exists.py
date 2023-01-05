import re

import pyblish.api

import openpype.api
from openpype.pipeline import legacy_io


class ValidateUSDShadeModelExists(pyblish.api.InstancePlugin):
    """Validate the Instance has no current cooking errors."""

    order = openpype.api.ValidateContentsOrder
    hosts = ["houdini"]
    families = ["usdShade"]
    label = "USD Shade model exists"

    def process(self, instance):

        asset = instance.data["asset"]
        subset = instance.data["subset"]

        # Assume shading variation starts after a dot separator
        shade_subset = subset.split(".", 1)[0]
        model_subset = re.sub("^usdShade", "usdModel", shade_subset)

        asset_doc = legacy_io.find_one(
            {"name": asset, "type": "asset"},
            {"_id": True}
        )
        if not asset_doc:
            raise RuntimeError("Asset does not exist: %s" % asset)

        subset_doc = legacy_io.find_one(
            {
                "name": model_subset,
                "type": "subset",
                "parent": asset_doc["_id"],
            },
            {"_id": True}
        )
        if not subset_doc:
            raise RuntimeError(
                "USD Model subset not found: "
                "%s (%s)" % (model_subset, asset)
            )
