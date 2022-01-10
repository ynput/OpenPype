import openpype.api
from openpype.hosts.photoshop import api as photoshop


class ExtractSaveScene(openpype.api.Extractor):
    """Save scene before extraction."""

    order = openpype.api.Extractor.order - 0.49
    label = "Extract Save Scene"
    hosts = ["photoshop"]
    families = ["workfile"]

    def process(self, instance):
        photoshop.stub().save()
