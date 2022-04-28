import pyblish.api

import openpype.hosts.maya.api.action
from openpype.pipeline import legacy_io
import openpype.api


class ValidateRenderLayerAOVs(pyblish.api.InstancePlugin):
    """Validate created AOVs / RenderElement is registered in the database

    Each render element is registered as a subset which is formatted based on
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

    def process(self, instance):
        invalid = self.get_invalid(instance)
        if invalid:
            raise RuntimeError("Found unregistered subsets: {}".format(invalid))

    def get_invalid(self, instance):

        invalid = []

        asset_name = instance.data["asset"]
        render_passses = instance.data.get("renderPasses", [])
        for render_pass in render_passses:
            is_valid = self.validate_subset_registered(asset_name, render_pass)
            if not is_valid:
                invalid.append(render_pass)

        return invalid

    def validate_subset_registered(self, asset_name, subset_name):
        """Check if subset is registered in the database under the asset"""

        asset = legacy_io.find_one({"type": "asset", "name": asset_name})
        is_valid = legacy_io.find_one({
            "type": "subset",
            "name": subset_name,
            "parent": asset["_id"]
        })

        return is_valid
