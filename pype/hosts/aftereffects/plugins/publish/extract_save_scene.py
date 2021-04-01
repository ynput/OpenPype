import openpype.api
from avalon import aftereffects


class ExtractSaveScene(openpype.api.Extractor):
    """Save scene before extraction."""

    order = openpype.api.Extractor.order - 0.49
    label = "Extract Save Scene"
    hosts = ["aftereffects"]
    families = ["workfile"]

    def process(self, instance):
        aftereffects.stub().save()
