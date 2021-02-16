import pype.api
from avalon import photoshop


class ExtractSaveScene(pype.api.Extractor):
    """Save scene before extraction."""

    order = pype.api.Extractor.order - 0.49
    label = "Extract Save Scene"
    hosts = ["photoshop"]
    families = ["workfile"]

    def process(self, instance):
        photoshop.stub().save()
