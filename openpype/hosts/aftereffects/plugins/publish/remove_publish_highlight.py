import openpype.api
from openpype.hosts.aftereffects.api import get_stub


class RemovePublishHighlight(openpype.api.Extractor):
    """Clean utf characters which are not working in DL

        Published compositions are marked with unicode icon which causes
        problems on specific render environments. Clean it first, sent to
        rendering, add it later back to avoid confusion.
    """

    order = openpype.api.Extractor.order - 0.49  # just before save
    label = "Clean render comp"
    hosts = ["aftereffects"]
    families = ["render.farm"]

    def process(self, instance):
        stub = get_stub()
        self.log.debug("instance::{}".format(instance.data))
        item = instance.data
        comp_name = item["comp_name"].replace(stub.PUBLISH_ICON, '')
        stub.rename_item(item["comp_id"], comp_name)
        instance.data["comp_name"] = comp_name
