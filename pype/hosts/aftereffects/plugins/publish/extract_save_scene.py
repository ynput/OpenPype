import pype.api
from avalon import aftereffects


class ExtractSaveScene(pype.api.Extractor):
    """Save scene before extraction."""

    order = pype.api.Extractor.order - 0.49
    label = "Extract Save Scene"
    hosts = ["aftereffects"]
    families = ["workfile"]

    def process(self, instance):
        aftereffects.stub().save()
