import pyblish.api

from avalon import io


def validate_subset_exists(asset_name, subset_name):
    """Check subset exists in the database under the asset"""

    asset = io.find_one({"type": "asset", "name": asset_name},
                        {"_id": True})
    is_valid = io.find_one({
        "type": "subset",
        "name": subset_name,
        "parent": asset["_id"]
    }, {"_id": True})

    return is_valid


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

    def process(self, instance):

        asset_name = instance.data["asset"]
        render_passses = instance.data.get("renderPasses", [])
        invalid = []
        for render_pass in render_passses:
            is_valid = validate_subset_exists(asset_name, render_pass)
            if not is_valid:
                invalid.append(render_pass)

        if invalid:
            raise RuntimeError("Found unregistered subsets: "
                               "{}".format(invalid))
