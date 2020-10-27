from pyblish import api


class ValidateHierarchy(api.InstancePlugin):
    """Validate clip's hierarchy data.

    """

    order = api.ValidatorOrder
    families = ["clip", "shot"]
    label = "Validate Hierarchy"
    hosts = ["hiero"]

    def process(self, instance):
        asset_name = instance.data.get("asset", None)
        hierarchy = instance.data.get("hierarchy", None)
        parents = instance.data.get("parents", None)

        assert hierarchy, "Hierarchy Tag has to be set \
        and added to clip `{}`".format(asset_name)
        assert parents, "Parents build from Hierarchy Tag has \
        to be set and added to clip `{}`".format(asset_name)
