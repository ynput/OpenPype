import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.aftereffects.api import get_stub


class ExtractSaveScene(pyblish.api.ContextPlugin):
    """Save scene before extraction."""

    order = publish.Extractor.order - 0.48
    label = "Extract Save Scene"
    hosts = ["aftereffects"]

    def process(self, context):
        stub = get_stub()
        stub.save()
