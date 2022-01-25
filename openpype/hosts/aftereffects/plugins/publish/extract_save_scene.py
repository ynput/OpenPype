import openpype.api
from openpype.hosts.aftereffects.api import get_stub


class ExtractSaveScene(openpype.api.Extractor):
    """Save scene before extraction."""

    order = openpype.api.Extractor.order - 0.48
    label = "Extract Save Scene"
    hosts = ["aftereffects"]
    families = ["workfile"]

    def process(self, instance):
        stub = get_stub()
        stub.save()
