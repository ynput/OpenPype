import pype.api
from avalon import photoshop

from datetime import datetime
class ExtractSaveScene(pype.api.Extractor):
    """Save scene before extraction."""

    order = pype.api.Extractor.order - 0.49
    label = "Extract Save Scene"
    hosts = ["photoshop"]
    families = ["workfile"]

    def process(self, instance):
        start = datetime.now()
        photoshop.app().ActiveDocument.Save()
        self.log.info(
            "ExtractSaveScene took {}".format(datetime.now() - start))
