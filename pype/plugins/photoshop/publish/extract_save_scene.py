import pype.api
from avalon import photoshop

from pype.modules.websocket_server.clients.photoshop_client import \
      PhotoshopClientStub


class ExtractSaveScene(pype.api.Extractor):
    """Save scene before extraction."""

    order = pype.api.Extractor.order - 0.49
    label = "Extract Save Scene"
    hosts = ["photoshop"]
    families = ["workfile"]

    def process(self, instance):
        photoshop_client = PhotoshopClientStub()
        photoshop_client.save()
