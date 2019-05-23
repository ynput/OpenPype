from pyblish import api


class ValidateHierarchy(api.InstancePlugin):
    """Validate clip's hierarchy data.

    """

    order = api.ValidatorOrder
    families = ["clip"]
    label = "Validate Hierarchy"
    hosts = ["nukestudio"]

    def process(self, instance):
        asset_name = instance.data.get("asset", None)
        hierarchy = instance.data.get("hierarchy", None)

        assert hierarchy is not None, "Hierarchy Tag has to be set and added to clip `{}`".format(asset_name)
