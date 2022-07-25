import pyblish.api

from openpype.hosts.aftereffects.api import get_stub


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
        stub = get_stub()
        item = instance.data
        # comp name contains highlight icon
        stub.rename_item(item["comp_id"], item["comp_name"])
