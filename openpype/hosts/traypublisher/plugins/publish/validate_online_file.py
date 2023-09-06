# -*- coding: utf-8 -*-
import pyblish.api

from openpype.pipeline.publish import (
    ValidateContentsOrder,
    PublishValidationError,
    OptionalPyblishPluginMixin,
)
from openpype.client import get_subset_by_name


class ValidateOnlineFile(OptionalPyblishPluginMixin,
                         pyblish.api.InstancePlugin):
    """Validate that subset doesn't exist yet."""
    label = "Validate Existing Online Files"
    hosts = ["traypublisher"]
    families = ["online"]
    order = ValidateContentsOrder

    optional = True

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        project_name = instance.context.data["projectName"]
        asset_id = instance.data["assetEntity"]["_id"]
        subset = get_subset_by_name(
            project_name, instance.data["subset"], asset_id)

        if subset:
            raise PublishValidationError(
                "Subset to be published already exists.",
                title=self.label
            )
