import pyblish.api

from avalon import aftereffects


class AddPublishHighlight(pyblish.api.InstancePlugin):
    """
        Revert back rendered comp name and add publish highlight
    """

    label = "Add render highlight"
    order = pyblish.api.IntegratorOrder + 8.0
    hosts = ["aftereffects"]
    families = ["render.farm"]
    optional = True

    def process(self, instance):
        stub = aftereffects.stub()
        item = instance.data
        # comp name contains highlight icon
        stub.rename_item(item["comp_id"], item["comp_name"])
