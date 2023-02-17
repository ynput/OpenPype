# -*- coding: utf-8 -*-
import re

import pyblish.api

from openpype.client import get_subset_by_name
from openpype.pipeline import legacy_io
from openpype.pipeline.publish import ValidateContentsOrder
from openpype.pipeline import PublishValidationError


class ValidateUSDShadeModelExists(pyblish.api.InstancePlugin):
    """Validate the Instance has no current cooking errors."""

    order = ValidateContentsOrder
    hosts = ["houdini"]
    families = ["usdShade"]
    label = "USD Shade model exists"

    def process(self, instance):
        project_name = legacy_io.active_project()
        asset_name = instance.data["asset"]
        subset = instance.data["subset"]

        # Assume shading variation starts after a dot separator
        shade_subset = subset.split(".", 1)[0]
        model_subset = re.sub("^usdShade", "usdModel", shade_subset)

        asset_doc = instance.data.get("assetEntity")
        if not asset_doc:
            raise RuntimeError("Asset document is not filled on instance.")

        subset_doc = get_subset_by_name(
            project_name, model_subset, asset_doc["_id"], fields=["_id"]
        )
        if not subset_doc:
            raise PublishValidationError(
                ("USD Model subset not found: "
                 "{} ({})").format(model_subset, asset_name),
                title=self.label
            )
