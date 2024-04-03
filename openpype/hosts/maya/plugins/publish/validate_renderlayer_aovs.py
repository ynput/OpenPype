import pyblish.api

import openpype.hosts.maya.api.action
from openpype.client import get_subset_by_name
from openpype.pipeline import legacy_io
from openpype.pipeline.publish import (
    PublishValidationError,
    OptionalPyblishPluginMixin
)


class ValidateRenderLayerAOVs(pyblish.api.InstancePlugin,
                              OptionalPyblishPluginMixin):
    """Validate created AOVs / RenderElement is registered in the database

    Each render element is registered as a product which is formatted based on
    the render layer and the render element, example:

        <render layer>.<render element>

    This translates to something like this:

        CHAR.diffuse

    This check is needed to ensure the render output is still complete

    """

    order = pyblish.api.ValidatorOrder + 0.1
    label = "Render Passes / AOVs Are Registered"
    hosts = ["maya"]
    families = ["renderlayer"]
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]
    optional = False

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishValidationError(
                "Found unregistered subsets: {}".format(invalid))

    def get_invalid(self, instance):
        invalid = []

        project_name = legacy_io.active_project()
        asset_doc = instance.data["assetEntity"]
        render_passes = instance.data.get("renderPasses", [])
        for render_pass in render_passes:
            is_valid = self.validate_subset_registered(
                project_name, asset_doc, render_pass
            )
            if not is_valid:
                invalid.append(render_pass)

        return invalid

    def validate_subset_registered(self, project_name, asset_doc, subset_name):
        """Check if subset is registered in the database under the asset"""

        return get_subset_by_name(
            project_name, subset_name, asset_doc["_id"], fields=["_id"]
        )
