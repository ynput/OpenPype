import openpype.api
from avalon import aftereffects


class ExtractSaveScene(openpype.api.Extractor):
    """Save scene before extraction."""

    order = openpype.api.Extractor.order - 0.48
    label = "Extract Save Scene"
    hosts = ["aftereffects"]
    families = ["workfile"]

    def process(self, instance):
        stub = aftereffects.stub()
        stub.save()
